"""稽核流程編排：檢查可否稽核 → 匯入比對範圍 → 組 context → 執行規則 → 保存結果。

交易邊界在此：匯入完成先 commit；規則執行失敗（例如尚未設定模型）時 rollback，
不留下稽核批次與結果。規則一律依代碼經 `RULE_REGISTRY` 取得。
"""

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import Engine
from app.core.exceptions import (
    BusinessDateNotFoundError,
    NotAuditableError,
    PatientNotFoundError,
)
from app.crud import audit as audit_crud
from app.models.audit import AuditFinding, AuditRun
from app.schemas.audit import AuditDayRead, AuditDaysRead, AuditFindingRead
from app.services.audit.base import AuditContext, RuleResult, StructuredLLM
from app.services.audit.context import (
    NOT_AUDITABLE_REASON,
    AuditScope,
    PackageFileCheck,
    PatientDay,
    build_audit_context,
    comparison_dates,
    find_invalid_package_dates,
    is_auditable,
    load_patient_days,
)
from app.services.audit.rules import RULE_REGISTRY
from app.services.ingestion.importer import import_daily_package
from app.services.ingestion.sources import DataSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Execution:
    rule_code: str
    engine: Engine
    started_at: datetime
    finished_at: datetime


async def list_audit_days(
    session: AsyncSession, source: DataSource, patient_key: str
) -> AuditDaysRead:
    """列出病患所有有資料的業務日（由新到舊）、可否稽核與最新一筆稽核結果。

    只讀檔與查詢，不匯入資料。

    Raises:
        PatientNotFoundError: 病患沒有出現在任何可解析的 manifest。
    """
    days = await load_patient_days(source, patient_key)
    if not days:
        raise PatientNotFoundError
    latest = await _latest_findings(session, patient_key)
    newest_first = sorted(days, key=lambda day: day.business_date, reverse=True)
    return AuditDaysRead(
        patient_key=patient_key,
        days=[_to_day_read(day, days, latest) for day in newest_first],
    )


async def run_patient_audit(  # noqa: PLR0913, PLR0917  規格固定的對外介面，測試以關鍵字參數呼叫
    session: AsyncSession,
    source: DataSource,
    llm: StructuredLLM,
    patient_key: str,
    business_date: date,
    rule_code: str,
) -> AuditFindingRead:
    """對一位病患的一個業務日執行稽核並保存結果。

    Raises:
        PatientNotFoundError: 病患沒有出現在任何可解析的 manifest。
        BusinessDateNotFoundError: 該日期不是此病患有資料的日期。
        NotAuditableError: 入院首日，沒有前日紀錄可比較。
        LLMNotConfiguredError: 尚未設定使用中的模型（不保存稽核批次與結果）。
    """
    days = await load_patient_days(source, patient_key)
    day = _find_auditable_day(days, business_date)
    scope = AuditScope(
        patient_key=patient_key,
        admission_id=day.admission_id,
        business_date=business_date,
        previous_dates=comparison_dates(day, days),
    )
    checks = await _import_packages(session, source, scope, days)
    await session.commit()

    invalid_dates = await find_invalid_package_dates(session, checks)
    ctx = await build_audit_context(session, scope, invalid_dates)
    rule = RULE_REGISTRY[rule_code](llm)
    if not rule.applies_to(ctx):
        raise NotAuditableError
    started_at = datetime.now(UTC)
    try:
        result = await rule.evaluate(ctx)
    except Exception:
        await session.rollback()
        raise
    execution = _Execution(rule.code, rule.engine, started_at, datetime.now(UTC))
    finding = await _save_result(session, ctx, result, execution)
    await session.commit()
    logger.info(
        "稽核完成：patient_key=%s rule_code=%s verdict=%s",
        patient_key,
        rule.code,
        finding.verdict,
    )
    return finding


def _find_auditable_day(days: Sequence[PatientDay], business_date: date) -> PatientDay:
    """在寫入任何資料之前檢查 E1、E2、E4。"""
    if not days:
        raise PatientNotFoundError
    day = next((day for day in days if day.business_date == business_date), None)
    if day is None:
        raise BusinessDateNotFoundError
    if not is_auditable(day, days):
        raise NotAuditableError
    return day


async def _import_packages(
    session: AsyncSession, source: DataSource, scope: AuditScope, days: Sequence[PatientDay]
) -> list[PackageFileCheck]:
    """匯入比對範圍內各日的資料包（已匯入的略過），回傳各日要檢查的病患檔。"""
    files = {day.business_date: day.file_name for day in days}
    checks: list[PackageFileCheck] = []
    for business_date in scope.all_dates:
        summary = await import_daily_package(session, source, business_date)
        checks.append(PackageFileCheck(business_date, summary.batch_id, files[business_date]))
    return checks


async def _save_result(
    session: AsyncSession, ctx: AuditContext, result: RuleResult, execution: _Execution
) -> AuditFindingRead:
    run = await audit_crud.add_run(
        session,
        AuditRun(
            rule_code=execution.rule_code,
            business_date=ctx.business_date,
            patient_key=ctx.patient_key,
            model=result.model,
            started_at=execution.started_at,
            finished_at=execution.finished_at,
        ),
    )
    finding = await audit_crud.add_finding(
        session,
        AuditFinding(
            audit_run_id=run.id,
            rule_code=execution.rule_code,
            patient_key=ctx.patient_key,
            business_date=ctx.business_date,
            verdict=result.verdict,
            message=result.message,
            evidence=[item.model_dump(mode="json") for item in result.evidence],
            note_similarities=[item.model_dump(mode="json") for item in result.note_similarities],
            engine=execution.engine,
            model=result.model,
            prompt_version=result.prompt_version,
            system_prompt_version=result.system_prompt_version,
            audited_at=execution.finished_at,
        ),
    )
    # commit 前先轉成 schema，避免 commit 後讀取過期欄位
    return AuditFindingRead.model_validate(finding)


async def _latest_findings(session: AsyncSession, patient_key: str) -> dict[date, AuditFindingRead]:
    """每個業務日最新的一筆稽核結果。"""
    latest: dict[date, AuditFindingRead] = {}
    for finding in await audit_crud.list_findings_newest_first(session, patient_key):
        if finding.business_date not in latest:
            latest[finding.business_date] = AuditFindingRead.model_validate(finding)
    return latest


def _to_day_read(
    day: PatientDay, days: Sequence[PatientDay], latest: Mapping[date, AuditFindingRead]
) -> AuditDayRead:
    auditable = is_auditable(day, days)
    return AuditDayRead(
        business_date=day.business_date,
        admission_id=day.admission_id,
        auditable=auditable,
        not_auditable_reason=None if auditable else NOT_AUDITABLE_REASON,
        latest_finding=latest.get(day.business_date),
    )
