"""稽核服務：固定流程、稽核週期、每日總覽。交易邊界在此（crud 不 commit）。

流程（見 docs/conventions/audit-rules.md）：
    build_audit_context → check_availability → build_input → complete_structured
    → Evidence 核對 → validate_output → 寫入 audit_runs／audit_findings

不適用或資料未提供時在第二步結束並照樣寫一筆紀錄，不呼叫 LLM。
任何非預期例外轉為 FAILED，訊息不含病歷內容；缺少使用中模型設定則直接回 409，不寫入紀錄。
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditCycle, AuditRunStatus, AvailabilityState, Verdict
from app.core.exceptions import (
    AppError,
    DayNotEndedError,
    LLMNotConfiguredError,
    LLMOutputError,
    NotFoundError,
    RuleSettledError,
)
from app.crud import audit_run as audit_run_crud
from app.models.audit import AuditRun
from app.schemas.audit import (
    AuditRuleStatusRead,
    AuditRunRead,
    AvailabilityRead,
    PatientAuditDayRead,
)
from app.schemas.llm_structured import LLMRequest, RuleOutput
from app.services.audit.clock import TodayProvider, is_day_ended, taipei_today
from app.services.audit.context import AuditContext, build_audit_context
from app.services.audit.evidence import verify_output
from app.services.audit.labels import AUDIT_CYCLE_LABELS, AVAILABILITY_LABELS
from app.services.audit.records import render_records_block
from app.services.audit.registry import RULE_REGISTRY
from app.services.audit.rules.base import AuditInput, AuditRule, Availability
from app.services.audit.runs import RunMeta, RunTarget, completed_run, needs_review_run, status_run
from app.services.audit.views import to_run_read
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm import gateway

logger = logging.getLogger(__name__)

RULE_NOT_FOUND_MESSAGE: Final = "查無此稽核項目"
OUTPUT_NEEDS_REVIEW_MESSAGE: Final = "模型輸出未通過格式或規則驗證，無法判定，請人工確認"
EXECUTION_FAILED_MESSAGE: Final = "稽核執行失敗，請稍後再試"
DAY_NOT_ENDED_MESSAGE: Final = "當日尚未結束，隔日起才能稽核"
RULE_SETTLED_MESSAGE: Final = "此項為每次入院一次的稽核，已完成，不可重複執行"
_SKIPPED_STATUS: Final = {
    AvailabilityState.NOT_APPLICABLE: AuditRunStatus.NOT_APPLICABLE,
    AvailabilityState.DATA_UNAVAILABLE: AuditRunStatus.DATA_UNAVAILABLE,
}
# 規則專屬欄位 = 輸出的其餘欄位，存入 details
_COMMON_OUTPUT_FIELDS: Final = frozenset(RuleOutput.model_fields)


class AuditService:
    """病患稽核的對外入口：每日總覽與單項執行。

    `today` 注入「今天」（測試用固定日期；正式用台北時間）。
    """

    def __init__(self, source: HospitalDataSource, today: TodayProvider = taipei_today) -> None:
        self._source = source
        self._today = today

    async def get_day_overview(
        self, session: AsyncSession, patient_key: str, business_date: date | None
    ) -> PatientAuditDayRead:
        """某日的稽核總覽；`business_date` 未指定時為已結束的最新一天（沒有時為最新一天）。

        Raises:
            NotFoundError: 查無病人，或該日沒有此病人的資料。
        """
        today = self._today()
        ctx = await build_audit_context(self._source, patient_key, business_date, today)
        rules = [await _rule_status(session, ctx, rule, today) for rule in RULE_REGISTRY.values()]
        previous_date, next_date = _neighbors(ctx.patient_dates, ctx.business_date)
        return PatientAuditDayRead(
            patient_key=ctx.patient_key,
            ward_code=ctx.ward_code,
            bed_code=ctx.bed_code,
            admitted_at=ctx.admitted_at,
            admitted_at_text=ctx.admitted_at_text,
            business_date=ctx.business_date,
            available_dates=list(ctx.patient_dates),
            previous_date=previous_date,
            next_date=next_date,
            rules=rules,
        )

    async def run_rule(
        self, session: AsyncSession, patient_key: str, business_date: date, rule_code: str
    ) -> AuditRunRead:
        """執行一項規則並寫入結果。

        Raises:
            NotFoundError: 查無規則、病人或該日資料。
            DayNotEndedError: 所選日期尚未結束（不寫入紀錄）。
            RuleSettledError: 一次性規則已完成（不寫入紀錄）。
            LLMNotConfiguredError: 需要 LLM 但沒有使用中的模型設定（不寫入紀錄）。
        """
        rule = _get_rule(rule_code)
        today = self._today()
        ctx = await build_audit_context(self._source, patient_key, business_date, today)
        if not is_day_ended(ctx.business_date, today):
            raise DayNotEndedError(DAY_NOT_ENDED_MESSAGE)
        rule_day = rule_day_on(rule, ctx, today)
        latest = await audit_run_crud.get_latest(
            session, patient_key, rule.code, rule_day.business_date
        )
        if _is_settled_once(rule, latest):
            raise RuleSettledError(RULE_SETTLED_MESSAGE)
        target = RunTarget(rule.code, patient_key, rule_day.business_date)
        run = await _execute(session, rule, ctx, target)
        await audit_run_crud.add(session, run)
        await session.commit()
        logger.info(
            "稽核完成：patient_key=%s rule=%s status=%s", patient_key, rule.code, run.status.value
        )
        return to_run_read(run, rule)


def effective_business_date(rule: AuditRule, ctx: AuditContext) -> date:
    """規則的寫入與查詢日期：一次性規則固定為入院日，其餘為畫面所選日期。

    院方沒有入院時間時，一次性規則退回所選日期。
    """
    if rule.cycle == AuditCycle.ONCE_PER_ADMISSION and ctx.admission_date is not None:
        return ctx.admission_date
    return ctx.business_date


async def _execute(
    session: AsyncSession, rule: AuditRule, ctx: AuditContext, target: RunTarget
) -> AuditRun:
    """執行並把例外轉成 FAILED；缺少模型設定則向上拋出（由 endpoint 回 409）。"""
    try:
        return await _run_checked(session, rule, ctx, target)
    except LLMNotConfiguredError:
        raise
    except AppError as error:
        logger.warning("稽核失敗：rule=%s error=%s", rule.code, type(error).__name__)
        return status_run(target, AuditRunStatus.FAILED, error.message)
    except Exception as error:
        # 只記例外類型；例外訊息可能含有病歷內容，不記錄
        logger.error("稽核未預期失敗：rule=%s error=%s", rule.code, type(error).__name__)
        return status_run(target, AuditRunStatus.FAILED, EXECUTION_FAILED_MESSAGE)


async def _run_checked(
    session: AsyncSession, rule: AuditRule, ctx: AuditContext, target: RunTarget
) -> AuditRun:
    availability = rule.check_availability(ctx.for_date(target.business_date))
    if availability.state != AvailabilityState.AVAILABLE:
        return status_run(target, _SKIPPED_STATUS[availability.state], availability.reason or "")
    return await _call_llm_rule(session, rule, ctx.for_date(target.business_date), target)


async def _call_llm_rule(
    session: AsyncSession, rule: AuditRule, ctx: AuditContext, target: RunTarget
) -> AuditRun:
    audit_input = rule.build_input(ctx)
    request = LLMRequest(
        rule_code=rule.code,
        prompt_name=rule.prompt_name,
        prompt_version=rule.prompt_version,
        variables={
            **audit_input.variables,
            "records_block": render_records_block(audit_input.records),
        },
    )
    try:
        result = await gateway.complete_structured(session, request, rule.output_schema)
    except LLMOutputError:
        # 絕不靜默視為 PASS（llm.md 第 6 步）
        return needs_review_run(target, OUTPUT_NEEDS_REVIEW_MESSAGE)
    try:
        rule.validate_output(result.parsed, audit_input)
    except LLMOutputError as error:
        # 規則的訊息是模組常數（不含病歷內容），保留給使用者看
        return needs_review_run(target, error.message)
    verified = verify_output(result.parsed, {r.record_id: r for r in audit_input.records})
    details = _details(result.parsed, audit_input)
    return completed_run(target, verified, details, RunMeta.from_result(result))


def _details(output: RuleOutput, audit_input: AuditInput) -> dict[str, object] | None:
    """結果的 details＝程式算出的 facts＋LLM 輸出的規則專屬欄位。"""
    extra = output.model_dump(mode="json", exclude=set(_COMMON_OUTPUT_FIELDS))
    return {**audit_input.facts, **extra} or None


@dataclass(frozen=True)
class RuleDay:
    """規則在某病患快照中的稽核日與可否執行；病患頁與病床總覽共用，不各自計算。"""

    business_date: date
    availability: Availability

    @property
    def can_run(self) -> bool:
        return self.availability.state == AvailabilityState.AVAILABLE


def rule_day_on(rule: AuditRule, ctx: AuditContext, today: date) -> RuleDay:
    """規則的稽核日（一次性規則為入院日）與該日的可否執行。

    可否執行以「畫面所選日期」（`ctx.business_date`）是否已結束判斷，不看一次性規則的入院日。
    病患頁與病床總覽都經由此函式，兩邊結果一致。
    """
    day = effective_business_date(rule, ctx)
    if not is_day_ended(ctx.business_date, today):
        return RuleDay(
            business_date=day,
            availability=Availability(AvailabilityState.DAY_NOT_ENDED, DAY_NOT_ENDED_MESSAGE),
        )
    return RuleDay(business_date=day, availability=rule.check_availability(ctx.for_date(day)))


async def _rule_status(
    session: AsyncSession, ctx: AuditContext, rule: AuditRule, today: date
) -> AuditRuleStatusRead:
    rule_day = rule_day_on(rule, ctx, today)
    latest = await audit_run_crud.get_latest(
        session, ctx.patient_key, rule.code, rule_day.business_date
    )
    # 一次性規則已 settled 後不可再執行；一鍵稽核也不納入（見 _is_settled_once）
    can_run = rule_day.can_run and not _is_settled_once(rule, latest)
    return AuditRuleStatusRead(
        rule_code=rule.code,
        name=rule.name,
        description=rule.description,
        cycle=rule.cycle,
        cycle_label=AUDIT_CYCLE_LABELS[rule.cycle],
        effective_business_date=rule_day.business_date,
        availability=_availability_read(rule_day.availability),
        can_run=can_run,
        include_in_run_all=can_run,
        latest_run=to_run_read(latest, rule) if latest is not None else None,
    )


def _is_settled_once(rule: AuditRule, latest: AuditRun | None) -> bool:
    """一次性規則是否已完成稽核（settled）；settled 後不可再執行，一鍵稽核也不納入。

    例外：模型輸出未通過驗證（COMPLETED 且判定為 NEEDS_REVIEW、附有原因）不算 settled，仍可重跑。
    """
    return (
        rule.cycle == AuditCycle.ONCE_PER_ADMISSION
        and latest is not None
        and latest.status == AuditRunStatus.COMPLETED
        and not _is_validation_failure(latest)
    )


def _is_validation_failure(run: AuditRun) -> bool:
    """LLM 輸出未通過格式或規則驗證（見 `runs.needs_review_run`）。"""
    return run.verdict == Verdict.NEEDS_REVIEW and bool(run.status_reason)


def _availability_read(availability: Availability) -> AvailabilityRead:
    return AvailabilityRead(
        state=availability.state,
        label=AVAILABILITY_LABELS[availability.state],
        reason=availability.reason,
    )


def _neighbors(dates: tuple[date, ...], day: date) -> tuple[date | None, date | None]:
    """所選日期前後一個有資料的日期（不是日曆上的前後一天）。"""
    previous_dates = [item for item in dates if item < day]
    next_dates = [item for item in dates if item > day]
    return (
        max(previous_dates) if previous_dates else None,
        min(next_dates) if next_dates else None,
    )


def _get_rule(rule_code: str) -> AuditRule:
    rule = RULE_REGISTRY.get(rule_code)
    if rule is None:
        raise NotFoundError(RULE_NOT_FOUND_MESSAGE)
    return rule
