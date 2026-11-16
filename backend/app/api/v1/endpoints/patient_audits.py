"""病患稽核 API：某日總覽與單項執行。endpoint 只解析輸入、呼叫 service、回傳結果。"""

from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.api.deps import AuditServiceDep, DbSession
from app.core.constants import PATIENT_KEY_PATTERN, RULE_CODE_PATTERN
from app.schemas.audit import AuditRunRead, PatientAuditDayRead

router = APIRouter(prefix="/patients", tags=["稽核"])

PatientKey = Annotated[str, Path(pattern=PATIENT_KEY_PATTERN, description="病患匿名鍵")]
RuleCode = Annotated[str, Path(pattern=RULE_CODE_PATTERN, description="稽核規則代碼，例如 R03")]
BusinessDate = Annotated[date, Path(description="稽核日期（YYYY-MM-DD）")]


@dataclass(frozen=True)
class RuleRunPath:
    """執行規則的路徑參數；集中成一個物件，讓 endpoint 參數數量維持在上限內。"""

    patient_key: str
    business_date: date
    rule_code: str


def _rule_run_path(
    patient_key: PatientKey, business_date: BusinessDate, rule_code: RuleCode
) -> RuleRunPath:
    return RuleRunPath(patient_key=patient_key, business_date=business_date, rule_code=rule_code)


RuleRunPathDep = Annotated[RuleRunPath, Depends(_rule_run_path)]


@router.get(
    "/{patient_key}/audits",
    response_model=PatientAuditDayRead,
    summary="取得病患某日的稽核總覽",
)
async def get_patient_audits(
    patient_key: PatientKey,
    service: AuditServiceDep,
    session: DbSession,
    business_date: Annotated[
        date | None, Query(description="稽核日期；未指定為病人最新一天")
    ] = None,
) -> PatientAuditDayRead:
    return await service.get_day_overview(session, patient_key, business_date)


@router.post(
    "/{patient_key}/audits/{business_date}/rules/{rule_code}/runs",
    response_model=AuditRunRead,
    status_code=status.HTTP_201_CREATED,
    summary="執行一項稽核規則並回傳結果",
)
async def run_patient_audit_rule(
    path: RuleRunPathDep,
    service: AuditServiceDep,
    session: DbSession,
) -> AuditRunRead:
    return await service.run_rule(session, path.patient_key, path.business_date, path.rule_code)
