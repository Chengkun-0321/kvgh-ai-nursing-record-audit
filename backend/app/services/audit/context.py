"""決定比對範圍、從 DB 組出 `AuditContext`（ORM 資料一律轉成不可變的值物件）。"""

import json
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.crud import clinical_record as clinical_record_crud
from app.crud import ingestion as ingestion_crud
from app.models.clinical_record import LabResult, NursingProgressNote, Tube, VitalSign
from app.schemas.ingestion import ManifestPatient
from app.services.audit.base import (
    AuditContext,
    LabResultRecord,
    ProgressNoteRecord,
    TubeRecord,
    VitalSignRecord,
)
from app.services.ingestion.sources import DataSource, parse_manifest

logger = logging.getLogger(__name__)

NOT_AUDITABLE_REASON: Final = "入院首日，無前日紀錄可比較"
# 病患檔無法讀取或沒有住院序號時，視為獨立的一次住院
UNKNOWN_ADMISSION_ID: Final = ""


@dataclass(frozen=True)
class PatientDay:
    """病患出現在某一天的資料包清單中。"""

    business_date: date
    # manifest 中該病患的檔名
    file_name: str
    admission_id: str


@dataclass(frozen=True)
class AuditScope:
    """一次稽核的對象與比對範圍。"""

    patient_key: str
    admission_id: str
    business_date: date
    # 早於當日的資料日（由新到舊）
    previous_dates: tuple[date, ...]

    @property
    def all_dates(self) -> tuple[date, ...]:
        """當日在前，其後為前日。"""
        return (self.business_date, *self.previous_dates)


@dataclass(frozen=True)
class PackageFileCheck:
    """要檢查驗證錯誤的檔案：某日的匯入批次與該病患的檔名。"""

    business_date: date
    batch_id: uuid.UUID | None
    file_name: str


async def load_patient_days(source: DataSource, patient_key: str) -> list[PatientDay]:
    """列出病患出現在 manifest 的所有日期（由舊到新），只讀檔、不寫 DB。

    manifest 不存在、無法解析或不符格式的日期略過（E10）。
    """
    days: list[PatientDay] = []
    for business_date in source.list_business_dates():
        entry = await _manifest_entry(source, business_date, patient_key)
        if entry is None:
            continue
        admission_id = await _read_admission_id(source, business_date, entry.file)
        days.append(PatientDay(business_date, entry.file, admission_id))
    return days


def is_auditable(day: PatientDay, days: Sequence[PatientDay]) -> bool:
    """同一住院中有更早的資料日才可稽核。

    住院序號不明時視為可稽核，實際執行時會因病患檔不符格式而判定為無法判定（E9）。
    """
    if day.admission_id == UNKNOWN_ADMISSION_ID:
        return True
    return bool(_earlier_dates(day, days))


def comparison_dates(day: PatientDay, days: Sequence[PatientDay]) -> tuple[date, ...]:
    """同一住院中早於當日、最近的 N 個資料日（由新到舊，N 取自設定）。

    只從有資料包的日期中挑選，沒有資料的日期自然跳過。
    """
    if day.admission_id == UNKNOWN_ADMISSION_ID:
        return ()
    lookback_days = get_settings().R02_LOOKBACK_DAYS
    return tuple(_earlier_dates(day, days)[:lookback_days])


async def find_invalid_package_dates(
    session: AsyncSession, checks: Sequence[PackageFileCheck]
) -> tuple[date, ...]:
    """該病患檔在對應匯入批次中有驗證錯誤的日期（E9）。"""
    invalid: list[date] = []
    for check in checks:
        if check.batch_id is None:
            continue
        if await ingestion_crud.has_errors(session, check.batch_id, check.file_name):
            invalid.append(check.business_date)
    return tuple(invalid)


async def build_audit_context(
    session: AsyncSession, scope: AuditScope, invalid_package_dates: tuple[date, ...]
) -> AuditContext:
    """從 DB 取出同一病患、同一住院、比對範圍內日期的紀錄，組成 `AuditContext`。"""
    record_scope = clinical_record_crud.RecordScope(
        patient_key=scope.patient_key,
        admission_id=scope.admission_id,
        business_dates=scope.all_dates,
    )
    notes = await clinical_record_crud.list_progress_notes(session, record_scope)
    vital_signs = await clinical_record_crud.list_vital_signs(session, record_scope)
    lab_results = await clinical_record_crud.list_lab_results(session, record_scope)
    tubes = await clinical_record_crud.list_tubes(session, record_scope)
    return AuditContext(
        patient_key=scope.patient_key,
        admission_id=scope.admission_id,
        business_date=scope.business_date,
        previous_dates=scope.previous_dates,
        progress_notes=tuple(_to_note(note) for note in notes),
        vital_signs=tuple(_to_vital_sign(vital) for vital in vital_signs),
        lab_results=tuple(_to_lab_result(lab) for lab in lab_results),
        tubes=tuple(_to_tube(tube) for tube in tubes),
        invalid_package_dates=invalid_package_dates,
    )


def _earlier_dates(day: PatientDay, days: Sequence[PatientDay]) -> list[date]:
    return sorted(
        (
            other.business_date
            for other in days
            if other.admission_id == day.admission_id and other.business_date < day.business_date
        ),
        reverse=True,
    )


async def _manifest_entry(
    source: DataSource, business_date: date, patient_key: str
) -> ManifestPatient | None:
    manifest = parse_manifest(await source.fetch_manifest(business_date))
    if manifest is None:
        # 只記日期
        logger.warning("資料包清單無法使用，略過該日：business_date=%s", business_date)
        return None
    return manifest.find_patient(patient_key)


async def _read_admission_id(source: DataSource, business_date: date, file_name: str) -> str:
    documents = await source.fetch(business_date)
    document = next((doc for doc in documents if doc.file_name == file_name), None)
    if document is None or document.content is None:
        return UNKNOWN_ADMISSION_ID
    return _lenient_admission_id(document.content)


def _lenient_admission_id(content: bytes) -> str:
    """寬鬆讀取 `patient.admission_id`：JSON 可解析且為非空字串就採用。

    不因其他欄位不符格式而放棄。
    """
    try:
        data: object = json.loads(content)
    except ValueError:
        return UNKNOWN_ADMISSION_ID
    patient = data.get("patient") if isinstance(data, dict) else None
    admission_id = patient.get("admission_id") if isinstance(patient, dict) else None
    if isinstance(admission_id, str) and admission_id:
        return admission_id
    return UNKNOWN_ADMISSION_ID


def _to_note(note: NursingProgressNote) -> ProgressNoteRecord:
    return ProgressNoteRecord(
        record_id=note.record_id,
        business_date=note.business_date,
        recorded_at=note.recorded_at,
        title_category=note.title_category,
        title=note.title,
        content=note.content,
    )


def _to_vital_sign(vital: VitalSign) -> VitalSignRecord:
    return VitalSignRecord(
        record_id=vital.record_id,
        business_date=vital.business_date,
        measured_at=vital.measured_at,
        body_temperature=vital.body_temperature,
        temperature_site=vital.temperature_site,
        pulse=vital.pulse,
        respiration=vital.respiration,
        sbp=vital.sbp,
        dbp=vital.dbp,
        spo2=vital.spo2,
        oxygen_therapy=vital.oxygen_therapy,
    )


def _to_lab_result(lab: LabResult) -> LabResultRecord:
    return LabResultRecord(
        record_id=lab.record_id,
        business_date=lab.business_date,
        order_name=lab.order_name,
        item=lab.item,
        value=lab.value,
        unit=lab.unit,
        reference_range=lab.reference_range,
        abnormal_flag=lab.abnormal_flag,
        collected_at=lab.collected_at,
    )


def _to_tube(tube: Tube) -> TubeRecord:
    return TubeRecord(
        tube_id=tube.tube_id,
        business_date=tube.business_date,
        tube_type=tube.tube_type,
        site=tube.site,
        size=tube.size,
        inserted_on=tube.inserted_on,
        removed_on=tube.removed_on,
        fixation=tube.fixation,
        appearance=tube.appearance,
    )
