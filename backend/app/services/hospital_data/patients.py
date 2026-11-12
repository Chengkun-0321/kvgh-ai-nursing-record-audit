"""病房清單、病人清單、病人摘要與原文（同步函式，由 service 放到 thread 執行）。"""

from datetime import date
from typing import Final

from app.schemas.hospital_data.patients import (
    CategoryCountRead,
    RawPatientDetailRead,
    RawPatientListRead,
    RawPatientSummaryRead,
    RawSourceRead,
    WardListRead,
    WardRead,
    WorkChecklistItemRead,
    WorkChecklistRead,
)
from app.schemas.hospital_data.raw import RawPatientFile
from app.services.hospital_data.events import CATEGORY_LABELS, admitted_at_text
from app.services.hospital_data.index import (
    PatientHistory,
    list_ward_dates,
    list_ward_histories,
    scan_ward_dates,
)
from app.services.hospital_data.source import HospitalDataSource
from app.services.hospital_data.timeline import count_events_by_category
from app.services.hospital_data.times import parse_record_time

_WORK_CHECKLIST_SECTION: Final = "工作清單"
_WORK_CHECKLIST_FILLED: Final = "有填寫"
# 院方資料沒有病房名稱，畫面以代碼組出名稱
_WARD_DISPLAY_NAME: Final = "{ward_code} 病房"


def ward_display_name(ward_code: str) -> str:
    """畫面上的病房名稱。"""
    return _WARD_DISPLAY_NAME.format(ward_code=ward_code)


def list_wards(source: HospitalDataSource, default_ward_code: str) -> WardListRead:
    """所有有院方資料的病房。"""
    wards = [_ward_read(source, code, dates) for code, dates in scan_ward_dates(source).items()]
    return WardListRead(default_ward_code=default_ward_code, wards=wards)


def list_raw_patients(source: HospitalDataSource, ward_code: str) -> RawPatientListRead:
    """某病房所有日期出現過的病人。"""
    ward_dates = list_ward_dates(source, ward_code)
    latest_date = ward_dates[-1]
    patients = [
        _patient_summary(source, history, latest_date)
        for history in list_ward_histories(source, ward_code, ward_dates)
    ]
    return RawPatientListRead(
        ward_code=ward_code,
        display_name=ward_display_name(ward_code),
        latest_business_date=latest_date,
        patients=patients,
    )


def build_patient_detail(
    source: HospitalDataSource, history: PatientHistory
) -> RawPatientDetailRead:
    """原始資料頁上方的病人摘要。"""
    latest_file = _latest_file(source, history)
    admitted_at = admitted_at_text(latest_file)
    counts = count_events_by_category(source, history)
    latest_ward_date = list_ward_dates(source, history.ward_code)[-1]
    return RawPatientDetailRead(
        patient_key=history.patient_key,
        ward_code=history.ward_code,
        bed_code=history.latest.bed_code,
        admitted_at_text=admitted_at,
        admitted_at=parse_record_time(admitted_at).occurred_at if admitted_at else None,
        is_current=history.latest.business_date == latest_ward_date,
        business_dates=[appearance.business_date for appearance in history.appearances],
        work_checklist=build_work_checklist(latest_file),
        category_counts=[
            CategoryCountRead(category=category, label=label, count=counts[category])
            for category, label in CATEGORY_LABELS.items()
        ],
    )


def read_patient_source(
    source: HospitalDataSource, history: PatientHistory, business_date: date | None
) -> RawSourceRead:
    """病人某日（未指定時為最新一天）資料檔的原文。"""
    appearance = history.latest if business_date is None else history.appearance_on(business_date)
    content = source.read_patient_text(
        appearance.business_date, history.ward_code, appearance.file_name
    )
    return RawSourceRead(
        patient_key=history.patient_key, business_date=appearance.business_date, content=content
    )


def build_work_checklist(patient_file: RawPatientFile) -> WorkChecklistRead:
    """工作清單各項是否已填寫。"""
    items = [
        WorkChecklistItemRead(label=label, value=value, is_filled=value == _WORK_CHECKLIST_FILLED)
        for label, value in patient_file.first_record(_WORK_CHECKLIST_SECTION).items()
    ]
    return WorkChecklistRead(
        items=items,
        filled_count=sum(item.is_filled for item in items),
        total_count=len(items),
    )


def _ward_read(source: HospitalDataSource, ward_code: str, dates: list[date]) -> WardRead:
    latest_list = source.read_patient_list(dates[-1], ward_code)
    return WardRead(
        ward_code=ward_code,
        display_name=ward_display_name(ward_code),
        business_dates=dates,
        latest_business_date=dates[-1],
        latest_patient_count=len(latest_list.patients),
    )


def _patient_summary(
    source: HospitalDataSource, history: PatientHistory, latest_ward_date: date
) -> RawPatientSummaryRead:
    latest_file = _latest_file(source, history)
    admitted_at = admitted_at_text(latest_file)
    checklist = build_work_checklist(latest_file)
    return RawPatientSummaryRead(
        patient_key=history.patient_key,
        bed_code=history.latest.bed_code,
        admitted_at_text=admitted_at,
        admitted_at=parse_record_time(admitted_at).occurred_at if admitted_at else None,
        first_business_date=history.appearances[0].business_date,
        last_business_date=history.latest.business_date,
        is_current=history.latest.business_date == latest_ward_date,
        work_checklist_filled_count=checklist.filled_count,
        work_checklist_total_count=checklist.total_count,
    )


def _latest_file(source: HospitalDataSource, history: PatientHistory) -> RawPatientFile:
    latest = history.latest
    return source.read_patient_file(latest.business_date, history.ward_code, latest.file_name)
