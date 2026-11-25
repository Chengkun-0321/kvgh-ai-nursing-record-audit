"""病床的稽核狀態：由各規則「最新一次且已完成」的結果算出床位狀態、進度與待處理發現。

純函式，不碰 DB 與院方檔；輸入是病患快照與批次查出的最新執行紀錄
（`crud.audit_run.list_latest_runs`）。
同一位病患在病患頁看到的結果與這裡使用的是同一組執行紀錄（同一套稽核日與查詢條件）。
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Final

from app.core.enums import AuditRunStatus, AvailabilityState, BedBoardStatus, RuleCellState, Verdict
from app.models.audit import AuditRun
from app.schemas.ward_board import (
    AuditFindingSummaryRead,
    BedStatusRead,
    PatientSummaryRead,
    RuleCellRead,
)
from app.services.audit.context import AuditContext
from app.services.audit.labels import AUDIT_RUN_STATUS_LABELS, AVAILABILITY_LABELS, VERDICT_LABELS
from app.services.audit.registry import RULE_REGISTRY
from app.services.audit.rules.base import AuditRule
from app.services.audit.running import RunningKey
from app.services.audit.service import RuleDay, rule_day_on
from app.services.audit.severity import VERDICT_SEVERITY, most_severe
from app.services.audit.views import finding_verdict_label, run_finding_labels

# (病患匿名鍵, 規則代碼, 稽核日)：唯一對應一列「最新一次執行」
RunKey = tuple[str, str, date]

NOT_AUDITED_LABEL: Final = "尚未稽核"
# 狀態列的顯示順序與名稱（由嚴重到正常，最後是尚未稽核）
STATUS_LABELS: Final[dict[BedBoardStatus, str]] = {
    BedBoardStatus.ERROR: VERDICT_LABELS[Verdict.ERROR],
    BedBoardStatus.WARNING: VERDICT_LABELS[Verdict.WARNING],
    BedBoardStatus.NEEDS_REVIEW: VERDICT_LABELS[Verdict.NEEDS_REVIEW],
    BedBoardStatus.PASS: VERDICT_LABELS[Verdict.PASS],
    BedBoardStatus.NOT_AUDITED: NOT_AUDITED_LABEL,
}
# 摘要文字中依嚴重度列出的判定
_SUMMARY_VERDICTS: Final = (Verdict.ERROR, Verdict.WARNING, Verdict.NEEDS_REVIEW)
# 尚無執行紀錄且當日不可稽核時，格子狀態對應可用性（AVAILABLE 不會用到）
_AVAILABILITY_CELL_STATES: Final[dict[AvailabilityState, RuleCellState]] = {
    AvailabilityState.NOT_APPLICABLE: RuleCellState.NOT_APPLICABLE,
    AvailabilityState.DATA_UNAVAILABLE: RuleCellState.DATA_UNAVAILABLE,
    AvailabilityState.DAY_NOT_ENDED: RuleCellState.DAY_NOT_ENDED,
}
# 待處理病床：已稽核且最嚴重判定不是 PASS
_PENDING_STATUSES: Final = frozenset(
    {BedBoardStatus.ERROR, BedBoardStatus.WARNING, BedBoardStatus.NEEDS_REVIEW}
)


@dataclass(frozen=True)
class BedSnapshot:
    """一張病床的院方資料快照；讀取院方檔（同步 I/O）已在呼叫端完成。"""

    bed_code: str
    patient: PatientSummaryRead
    ctx: AuditContext

    @property
    def patient_key(self) -> str:
        return self.ctx.patient_key


@dataclass(frozen=True)
class _RuleOutcome:
    """保留最新執行供格子顯示，已完成結果則供既有床位狀態與進度使用。"""

    rule: AuditRule
    rule_day: RuleDay
    completed_run: AuditRun | None
    latest_run: AuditRun | None

    @property
    def is_audited(self) -> bool:
        return self.rule_day.can_run and self.completed_run is not None


def run_key(run: AuditRun) -> RunKey:
    """執行紀錄對應的查詢鍵。"""
    return (run.patient_key, run.rule_code, run.business_date)


def build_bed_status(
    bed: BedSnapshot,
    latest: Mapping[RunKey, AuditRun],
    today: date,
    is_running: Callable[[RunningKey], bool],
) -> BedStatusRead:
    """組出床位與格子狀態；日期、最新紀錄與執行中查詢皆由呼叫端注入。"""
    outcomes = [_outcome(rule, bed.ctx, latest, today) for rule in RULE_REGISTRY.values()]
    completed = [o.completed_run for o in outcomes if o.completed_run is not None]
    status = _status_of(completed)
    pending = _pending_findings(outcomes)
    audited = sum(outcome.is_audited for outcome in outcomes)
    auditable = sum(outcome.rule_day.can_run for outcome in outcomes)
    return BedStatusRead(
        bed_code=bed.bed_code,
        patient=bed.patient,
        status=status,
        status_label=STATUS_LABELS[status],
        summary_text=_summary_text(status, pending),
        is_pending=status in _PENDING_STATUSES,
        pending_findings=pending,
        empty_findings_text=_empty_findings_text(status, pending),
        audited_rule_count=audited,
        auditable_rule_count=auditable,
        audit_progress_text=_progress_text(audited, auditable),
        rule_cells=[
            _rule_cell(
                outcome,
                is_running(
                    RunningKey(bed.patient_key, outcome.rule.code, outcome.rule_day.business_date)
                ),
            )
            for outcome in outcomes
        ],
    )


def _outcome(
    rule: AuditRule, ctx: AuditContext, latest: Mapping[RunKey, AuditRun], today: date
) -> _RuleOutcome:
    rule_day = rule_day_on(rule, ctx, today)
    run = latest.get((ctx.patient_key, rule.code, rule_day.business_date))
    # 最新一次為 FAILED、NOT_APPLICABLE 或 DATA_UNAVAILABLE 都不算已完成
    completed = run if run is not None and run.status == AuditRunStatus.COMPLETED else None
    return _RuleOutcome(rule=rule, rule_day=rule_day, completed_run=completed, latest_run=run)


def _rule_cell(outcome: _RuleOutcome, is_running: bool) -> RuleCellRead:
    """依執行中、最新結果、可用性順序顯示；已完成結果不受當日可用性影響。"""
    cell = RuleCellRead(
        rule_code=outcome.rule.code,
        state=RuleCellState.NOT_AUDITED,
        label=NOT_AUDITED_LABEL,
        verdict=None,
        finding_count=0,
    )
    if is_running:
        return cell.model_copy(update={"state": RuleCellState.RUNNING, "label": "稽核中"})
    run = outcome.latest_run
    if run is not None:
        return _run_cell(cell, run)
    availability = outcome.rule_day.availability.state
    if availability != AvailabilityState.AVAILABLE:
        return cell.model_copy(
            update={
                "state": _AVAILABILITY_CELL_STATES[availability],
                "label": AVAILABILITY_LABELS[availability],
            }
        )
    return cell


def _run_cell(cell: RuleCellRead, run: AuditRun) -> RuleCellRead:
    """最新執行的格子只在已完成時帶判定與發現數，其餘使用執行狀態標籤。"""
    if run.status == AuditRunStatus.COMPLETED:
        if run.verdict is None:
            return cell
        return cell.model_copy(
            update={
                "state": RuleCellState(run.verdict.value),
                "label": VERDICT_LABELS[run.verdict],
                "verdict": run.verdict,
                "finding_count": sum(finding.verdict != Verdict.PASS for finding in run.findings),
            }
        )
    return cell.model_copy(
        update={
            "state": RuleCellState(run.status.value),
            "label": AUDIT_RUN_STATUS_LABELS[run.status],
        }
    )


def _status_of(runs: list[AuditRun]) -> BedBoardStatus:
    verdicts = [run.verdict for run in runs if run.verdict is not None]
    if not verdicts:
        return BedBoardStatus.NOT_AUDITED
    return BedBoardStatus(most_severe(verdicts).value)


def _pending_findings(outcomes: list[_RuleOutcome]) -> list[AuditFindingSummaryRead]:
    """已完成結果中判定不是 PASS 的發現；依嚴重度（高到低）、規則順序、發現順序排列。"""
    entries: list[tuple[int, int, int, AuditFindingSummaryRead]] = []
    for rule_index, outcome in enumerate(outcomes):
        run = outcome.completed_run
        if run is None:
            continue
        labels = run_finding_labels(outcome.rule, run.details)
        for finding in run.findings:
            if finding.verdict == Verdict.PASS:
                continue
            summary = AuditFindingSummaryRead(
                rule_code=run.rule_code,
                verdict=finding.verdict,
                verdict_label=finding_verdict_label(finding, labels),
                message=finding.message,
                recorded_at=run.created_at,
            )
            entries.append(
                (VERDICT_SEVERITY[finding.verdict], rule_index, finding.position, summary)
            )
    entries.sort(key=lambda entry: (-entry[0], entry[1], entry[2]))
    return [summary for _, _, _, summary in entries]


def _summary_text(status: BedBoardStatus, pending: list[AuditFindingSummaryRead]) -> str:
    """床位卡片上的摘要，例：「缺漏 1 項・需確認 2 項」；沒有待處理發現時為狀態名稱。"""
    parts = [
        f"{VERDICT_LABELS[verdict]} {count} 項"
        for verdict in _SUMMARY_VERDICTS
        if (count := _count_verdict(pending, verdict)) > 0
    ]
    return "・".join(parts) if parts else STATUS_LABELS[status]


def _count_verdict(pending: list[AuditFindingSummaryRead], verdict: Verdict) -> int:
    return sum(finding.verdict == verdict for finding in pending)


def _empty_findings_text(status: BedBoardStatus, pending: list[AuditFindingSummaryRead]) -> str:
    """沒有待處理發現時，詳情清單顯示的文字。

    判定不是 PASS 但沒有任何發現（例如 LLM 輸出未通過驗證）時，不可說「皆無待確認事項」。
    """
    if pending:
        return ""
    if status == BedBoardStatus.NOT_AUDITED:
        return "此床尚未執行稽核，目前沒有稽核結果"
    if status == BedBoardStatus.PASS:
        return "今日稽核項目皆無待確認事項"
    return f"判定為{STATUS_LABELS[status]}，但沒有具體發現，請至病患頁查看說明"


def _progress_text(audited: int, auditable: int) -> str:
    if auditable == 0:
        return "今日無可稽核項目"
    return f"已稽核 {audited}／{auditable} 項"
