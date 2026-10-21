"""病患每日資料檔（對照 patient-daily.schema.json）。

R02 需要的區塊（patient、nursing_progress_notes、vital_signs、lab_results、tubes）會正規化入庫；
其他區塊只驗證並保留原始檔。
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from app.schemas.ingestion.assessment import AdmissionAssessment, DailyPhysicalAssessment
from app.schemas.ingestion.common import (
    IngestionModel,
    NonEmptyStr,
    NullableDate,
    NullableDateTime,
    NullableStr,
    PatientStatus,
    SchemaVersion,
    StaffId,
)


class Ward(IngestionModel):
    """病房。"""

    ward_code: NonEmptyStr
    ward_name: NonEmptyStr


class Patient(IngestionModel):
    """病人基本資料（去識別）。"""

    patient_id: NonEmptyStr
    admission_id: NonEmptyStr
    bed_code: NonEmptyStr
    sex: Literal["M", "F"]
    age_years: Annotated[int, Field(ge=0, le=130)]
    admission_at: AwareDatetime
    admission_source: Literal["急診", "門診", "轉院", "其他"]
    admission_diagnosis: NonEmptyStr
    attending_physician_id: StaffId
    status: PatientStatus
    status_changed_at: NullableDateTime


class NursingProgressNote(IngestionModel):
    """護理過程紀錄。"""

    record_id: NonEmptyStr
    recorded_at: AwareDatetime
    title_category: Literal[
        "健康問題",
        "交班",
        "導管照護",
        "會診",
        "營養照會建議",
        "轉出摘要",
        "轉入摘要",
        "入院護理",
        "出院護理",
        "護理指導",
        "其他",
    ]
    title: NonEmptyStr
    content: str
    author_id: StaffId
    last_modified_at: NullableDateTime
    has_image: bool


class Transfer(IngestionModel):
    """轉入／轉出。"""

    transfer_id: NonEmptyStr
    direction: Literal["in", "out"]
    occurred_at: AwareDatetime
    from_unit: NonEmptyStr
    to_unit: NonEmptyStr
    reason: NullableStr


class Consultation(IngestionModel):
    """會診。"""

    consultation_id: NonEmptyStr
    consultant_role: Literal["醫師", "營養師"]
    department: NonEmptyStr
    consult_type: Literal["REGULAR", "URGENT"]
    ordered_at: AwareDatetime
    requested_by: StaffId
    signed_at: NullableDateTime
    signed_by: StaffId | None
    replied_at: NullableDateTime
    status: Literal["未簽收", "已簽收", "已回覆"]
    condition_summary: NullableStr
    reply_content: NullableStr


class MedicationAdministration(IngestionModel):
    """給藥執行。"""

    administration_id: NonEmptyStr
    administered_at: AwareDatetime
    administered_by: StaffId
    dose: float | None
    unit: NullableStr
    rate: NullableStr
    status: Literal["已執行", "暫停", "停止", "拒絕", "未執行"]
    remark: NullableStr


class MedicationOrder(IngestionModel):
    """藥囑與當天給藥。"""

    order_id: NonEmptyStr
    order_category: Literal["常規", "臨時"]
    drug_name: NonEmptyStr
    route: NonEmptyStr
    dose: float
    unit: NonEmptyStr
    frequency: NonEmptyStr
    is_high_alert: bool
    ordered_at: AwareDatetime
    prescriber_id: StaffId
    status: Literal["未執行", "執行中", "已執行", "到期停用", "DC"]
    administrations: list[MedicationAdministration]


class VitalSign(IngestionModel):
    """生命徵象。"""

    record_id: NonEmptyStr
    measured_at: AwareDatetime
    body_temperature: float | None
    temperature_site: Literal["耳溫", "口溫", "腋溫", "肛溫"] | None
    pulse: int | None
    respiration: int | None
    sbp: int | None
    dbp: int | None
    spo2: int | None
    oxygen_therapy: NullableStr
    measured_by: StaffId


class LabResult(IngestionModel):
    """檢驗結果。"""

    record_id: NonEmptyStr
    order_name: NonEmptyStr
    item: NonEmptyStr
    value: str
    unit: NullableStr
    reference_range: NullableStr
    abnormal_flag: Literal["H", "L"] | None
    collected_at: AwareDatetime
    reported_at: NullableDateTime


class Tube(IngestionModel):
    """管路（當天現況）。"""

    tube_id: NonEmptyStr
    tube_type: NonEmptyStr
    site: NonEmptyStr
    size: NullableStr
    inserted_on: NullableDate
    removed_on: NullableDate
    fixation: NullableStr
    appearance: NullableStr


class Examination(IngestionModel):
    """檢查醫囑（選填區塊）。"""

    order_id: NonEmptyStr
    order_name: NonEmptyStr
    ordered_at: AwareDatetime
    performed_at: NullableDateTime
    status: Literal["已開立", "已執行", "正式報告", "取消"]
    is_invasive: bool
    report_summary: NullableStr


class HealthEducation(IngestionModel):
    """護理指導（選填區塊）。"""

    record_id: NonEmptyStr
    recorded_at: AwareDatetime
    topic: NonEmptyStr
    target: Literal["病人", "家屬", "病人及家屬"]
    content: str
    author_id: StaffId


class ConsentForm(IngestionModel):
    """同意書（選填區塊）。"""

    consent_id: NonEmptyStr
    form_name: NonEmptyStr
    related_order_id: NullableStr
    status: Literal["待簽", "已簽", "拒簽"]
    signed_at: NullableDateTime


class EmotionalDistressAssessment(IngestionModel):
    """情緒困擾評估（選填區塊）。"""

    record_id: NonEmptyStr
    assessed_at: AwareDatetime
    score: Annotated[int, Field(ge=0, le=10)]
    suicidal_ideation: bool | None
    author_id: StaffId


class PatientDaily(IngestionModel):
    """一位病患一天的資料檔。"""

    schema_version: SchemaVersion
    business_date: date
    ward: Ward
    patient: Patient
    admission_assessment: AdmissionAssessment | None
    daily_physical_assessments: list[DailyPhysicalAssessment]
    nursing_progress_notes: list[NursingProgressNote]
    transfers: list[Transfer]
    consultations: list[Consultation]
    medication_orders: list[MedicationOrder]
    vital_signs: list[VitalSign]
    lab_results: list[LabResult]
    tubes: list[Tube]
    # 選填區塊（候選稽核項目用）：可省略，出現時必須符合格式
    examinations: list[Examination] = Field(default_factory=list)
    health_educations: list[HealthEducation] = Field(default_factory=list)
    consent_forms: list[ConsentForm] = Field(default_factory=list)
    emotional_distress_assessments: list[EmotionalDistressAssessment] = Field(default_factory=list)
