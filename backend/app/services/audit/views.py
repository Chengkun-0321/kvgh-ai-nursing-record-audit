"""ORM 紀錄 → 回應結構；狀態文字在此對照，前端不另算。

病患頁（`to_run_read`）與病床總覽（`ward_board_status`）共用發現的顯示文字，不各自複製。
"""

from collections.abc import Mapping

from app.core.enums import Verdict
from app.models.audit import AuditFinding, AuditRun
from app.schemas.audit import AuditFindingRead, AuditRunRead, Evidence
from app.services.audit.labels import AUDIT_RUN_STATUS_LABELS, VERDICT_LABELS
from app.services.audit.rules.base import AuditRule, LabelsFindings


def to_run_read(run: AuditRun, rule: AuditRule) -> AuditRunRead:
    """一次執行的回應結構（發現需已載入）。"""
    labels = run_finding_labels(rule, run.details)
    return AuditRunRead(
        id=run.id,
        rule_code=run.rule_code,
        rule_name=rule.name,
        patient_key=run.patient_key,
        business_date=run.business_date,
        status=run.status,
        status_label=AUDIT_RUN_STATUS_LABELS[run.status],
        status_reason=run.status_reason,
        verdict=run.verdict,
        verdict_label=VERDICT_LABELS[run.verdict] if run.verdict else None,
        summary=run.summary,
        findings=[_finding_read(finding, labels) for finding in run.findings],
        details=run.details,
        model=run.model,
        prompt_version=run.prompt_version,
        system_prompt_version=run.system_prompt_version,
        duration_ms=run.duration_ms,
        created_at=run.created_at,
    )


def run_finding_labels(rule: AuditRule, details: Mapping[str, object] | None) -> Mapping[str, str]:
    """規則為某次執行的發現指定的專屬文字（「發現項目 → 顯示文字」）；規則沒有指定時為空。"""
    return rule.finding_labels(details) if isinstance(rule, LabelsFindings) else {}


def finding_verdict_label(finding: AuditFinding, labels: Mapping[str, str]) -> str:
    """PASS 與 NEEDS_REVIEW 可使用規則指定的文字；提醒類判定維持共同文字。

    Args:
        finding: 含判定與項目名稱的發現。
        labels: 規則指定的「發現項目 → 顯示文字」，未指定時可為空。

    Returns:
        可套用的規則文字，未指定或不允許取代時回傳共同文字。
    """
    default = VERDICT_LABELS[finding.verdict]
    # 提醒類判定不得被規則文字淡化，僅允許 PASS 與 NEEDS_REVIEW 使用專屬文字。
    if finding.verdict not in (Verdict.PASS, Verdict.NEEDS_REVIEW):
        return default
    return labels.get(finding.item, default)


def _finding_read(finding: AuditFinding, labels: Mapping[str, str]) -> AuditFindingRead:
    return AuditFindingRead(
        position=finding.position,
        item=finding.item,
        verdict=finding.verdict,
        verdict_label=finding_verdict_label(finding, labels),
        message=finding.message,
        evidence=[Evidence.model_validate(evidence) for evidence in finding.evidence],
    )
