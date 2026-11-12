"""原始資料頁的病人 API：摘要、時間軸、檢驗矩陣、原文。"""

from datetime import date
from typing import Annotated, Final

from fastapi import APIRouter, Path, Query

from app.api.deps import HospitalData
from app.core.enums import RawRecordCategory
from app.schemas.hospital_data.patients import RawPatientDetailRead, RawSourceRead
from app.schemas.hospital_data.timeline import LabMatrixRead, PatientTimelineRead
from app.services.hospital_data import raw_data_service
from app.services.hospital_data.timeline import TimelineFilter

router = APIRouter(prefix="/raw-patients", tags=["原始資料"])

PATIENT_KEY_PATTERN: Final = r"^[0-9A-Za-z]{1,32}$"
PatientKey = Annotated[str, Path(pattern=PATIENT_KEY_PATTERN, description="病患匿名鍵")]
StartDate = Annotated[date | None, Query(description="起始日期（含）")]
EndDate = Annotated[date | None, Query(description="結束日期（含）")]


@router.get("/{patient_key}", response_model=RawPatientDetailRead, summary="取得病人摘要")
async def get_patient_detail(patient_key: PatientKey, source: HospitalData) -> RawPatientDetailRead:
    return await raw_data_service.get_patient_detail(source, patient_key)


@router.get(
    "/{patient_key}/timeline",
    response_model=PatientTimelineRead,
    summary="取得病人所有日期合併後的時間軸",
)
async def get_patient_timeline(
    *,
    patient_key: PatientKey,
    source: HospitalData,
    start_date: StartDate = None,
    end_date: EndDate = None,
    categories: Annotated[list[RawRecordCategory] | None, Query(description="紀錄類別")] = None,
) -> PatientTimelineRead:
    timeline_filter = TimelineFilter(
        start_date=start_date,
        end_date=end_date,
        categories=frozenset(categories) if categories else None,
    )
    return await raw_data_service.get_patient_timeline(source, patient_key, timeline_filter)


@router.get(
    "/{patient_key}/lab-matrix",
    response_model=LabMatrixRead,
    summary="取得病人檢驗報告的項目 × 時間矩陣",
)
async def get_lab_matrix(
    patient_key: PatientKey,
    source: HospitalData,
    start_date: StartDate = None,
    end_date: EndDate = None,
) -> LabMatrixRead:
    timeline_filter = TimelineFilter(start_date=start_date, end_date=end_date)
    return await raw_data_service.get_lab_matrix(source, patient_key, timeline_filter)


@router.get(
    "/{patient_key}/source", response_model=RawSourceRead, summary="取得病人某日資料檔的原文"
)
async def get_patient_source(
    patient_key: PatientKey,
    source: HospitalData,
    business_date: Annotated[date | None, Query(description="資料日期；未指定為最新一天")] = None,
) -> RawSourceRead:
    return await raw_data_service.get_patient_source(source, patient_key, business_date)
