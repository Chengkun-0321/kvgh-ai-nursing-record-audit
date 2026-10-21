"""把驗證過的病患檔轉成內部資料表的欄位（只處理 R02 需要的區塊）。

院方時間帶 `+08:00`，一律轉 UTC 儲存；`business_date` 為該筆所屬資料包的業務日期。
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime

from app.db.base import Base
from app.models.admission import Admission
from app.models.clinical_record import LabResult, NursingProgressNote, Tube, VitalSign
from app.schemas.ingestion import PatientDaily
from app.schemas.ingestion import patient_daily as source


@dataclass(frozen=True)
class NormalizedRow:
    """一列資料：自然鍵與其餘欄位。"""

    natural_key: Mapping[str, object]
    values: Mapping[str, object]


NormalizedTable = tuple[type[Base], list[NormalizedRow]]


def normalize_patient_daily(daily: PatientDaily, business_date: date) -> list[NormalizedTable]:
    """轉成住院、護理過程紀錄、生命徵象、檢驗、管路的資料列。

    Args:
        daily: 驗證過的病患檔。
        business_date: 資料包的業務日期。

    Returns:
        各資料表與其資料列；依自然鍵 upsert。
    """
    owner = {
        "patient_key": daily.patient.patient_id,
        "admission_id": daily.patient.admission_id,
        "business_date": business_date,
    }
    return [
        (Admission, [_admission_row(daily.patient)]),
        (NursingProgressNote, [_note_row(note, owner) for note in daily.nursing_progress_notes]),
        (VitalSign, [_vital_sign_row(vital, owner) for vital in daily.vital_signs]),
        (LabResult, [_lab_result_row(lab, owner) for lab in daily.lab_results]),
        (Tube, [_tube_row(tube, owner) for tube in daily.tubes]),
    ]


def _to_utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _to_utc_or_none(value: datetime | None) -> datetime | None:
    return None if value is None else _to_utc(value)


def _admission_row(patient: source.Patient) -> NormalizedRow:
    return NormalizedRow(
        natural_key={"admission_id": patient.admission_id},
        values={
            "patient_key": patient.patient_id,
            "bed_code": patient.bed_code,
            "sex": patient.sex,
            "age_years": patient.age_years,
            "admission_at": _to_utc(patient.admission_at),
            "admission_source": patient.admission_source,
            "admission_diagnosis": patient.admission_diagnosis,
            "attending_physician_id": patient.attending_physician_id,
            "status": patient.status,
            "status_changed_at": _to_utc_or_none(patient.status_changed_at),
        },
    )


def _note_row(note: source.NursingProgressNote, owner: Mapping[str, object]) -> NormalizedRow:
    return NormalizedRow(
        natural_key={"record_id": note.record_id},
        values={
            **owner,
            "recorded_at": _to_utc(note.recorded_at),
            "title_category": note.title_category,
            "title": note.title,
            "content": note.content,
            "author_id": note.author_id,
            "last_modified_at": _to_utc_or_none(note.last_modified_at),
            "has_image": note.has_image,
        },
    )


def _vital_sign_row(vital: source.VitalSign, owner: Mapping[str, object]) -> NormalizedRow:
    return NormalizedRow(
        natural_key={"record_id": vital.record_id},
        values={
            **owner,
            "measured_at": _to_utc(vital.measured_at),
            "body_temperature": vital.body_temperature,
            "temperature_site": vital.temperature_site,
            "pulse": vital.pulse,
            "respiration": vital.respiration,
            "sbp": vital.sbp,
            "dbp": vital.dbp,
            "spo2": vital.spo2,
            "oxygen_therapy": vital.oxygen_therapy,
            "measured_by": vital.measured_by,
        },
    )


def _lab_result_row(lab: source.LabResult, owner: Mapping[str, object]) -> NormalizedRow:
    return NormalizedRow(
        natural_key={"record_id": lab.record_id},
        values={
            **owner,
            "order_name": lab.order_name,
            "item": lab.item,
            "value": lab.value,
            "unit": lab.unit,
            "reference_range": lab.reference_range,
            "abnormal_flag": lab.abnormal_flag,
            "collected_at": _to_utc(lab.collected_at),
            "reported_at": _to_utc_or_none(lab.reported_at),
        },
    )


def _tube_row(tube: source.Tube, owner: Mapping[str, object]) -> NormalizedRow:
    # 管路是每日現況清單：以 (tube_id, business_date) 為自然鍵，保留每天的狀態
    values = {key: value for key, value in owner.items() if key != "business_date"}
    return NormalizedRow(
        natural_key={"tube_id": tube.tube_id, "business_date": owner["business_date"]},
        values={
            **values,
            "tube_type": tube.tube_type,
            "site": tube.site,
            "size": tube.size,
            "inserted_on": tube.inserted_on,
            "removed_on": tube.removed_on,
            "fixation": tube.fixation,
            "appearance": tube.appearance,
        },
    )
