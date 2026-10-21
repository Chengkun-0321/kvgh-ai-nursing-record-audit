"""病患每日稽核 API：列出每日稽核狀態、手動執行單日稽核。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.constants import PATIENT_KEY_MAX_LENGTH
from app.schemas.audit import AuditDaysRead, AuditFindingRead, AuditRunCreate
from app.services.audit import runner
from app.services.audit.base import StructuredLLM
from app.services.ingestion.sources import DataSource, LocalFixtureSource
from app.services.llm import gateway

router = APIRouter(tags=["稽核"])


def get_data_source() -> DataSource:
    """每日資料包來源（目前為本機目錄）；只建構物件，不讀檔。"""
    return LocalFixtureSource(get_settings().MOCK_DATA_DIR)


def get_structured_llm() -> StructuredLLM:
    """稽核規則使用的結構化 LLM 呼叫。"""
    return gateway.complete_structured


Source = Annotated[DataSource, Depends(get_data_source)]
StructuredLlm = Annotated[StructuredLLM, Depends(get_structured_llm)]
PatientKeyPath = Annotated[str, Path(min_length=1, max_length=PATIENT_KEY_MAX_LENGTH)]


@router.get(
    "/patients/{patient_key}/audit-days",
    response_model=AuditDaysRead,
    summary="列出病患每日稽核狀態",
)
async def list_audit_days(
    patient_key: PatientKeyPath, db: DbSession, source: Source
) -> AuditDaysRead:
    return await runner.list_audit_days(db, source, patient_key)


@router.post(
    "/audit-runs",
    response_model=AuditFindingRead,
    status_code=status.HTTP_201_CREATED,
    summary="執行單日稽核（匯入資料後由 LLM 判斷）",
)
async def create_audit_run(
    payload: AuditRunCreate, db: DbSession, source: Source, llm: StructuredLlm
) -> AuditFindingRead:
    return await runner.run_patient_audit(
        session=db,
        source=source,
        llm=llm,
        patient_key=payload.patient_key,
        business_date=payload.business_date,
        rule_code=payload.rule_code,
    )
