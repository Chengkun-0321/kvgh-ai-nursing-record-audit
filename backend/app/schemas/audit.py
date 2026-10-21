"""稽核 API 的輸入與輸出結構。"""

import re
import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

from app.core.constants import PATIENT_KEY_MAX_LENGTH
from app.core.enums import Engine, Verdict

_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

IssueType = Literal["copy", "unchanged", "clinical_changed", "outdated_reference"]
PatientKey = Annotated[str, StringConstraints(min_length=1, max_length=PATIENT_KEY_MAX_LENGTH)]


def _with_utc(value: datetime) -> datetime:
    """SQLite 讀回的時間沒有時區；一律視為 UTC，輸出時帶時區。"""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class Evidence(BaseModel):
    """判定依據：來源、紀錄 ID、欄位、時間、原文片段。"""

    source: str
    record_id: str
    field: str | None
    recorded_at: datetime | None
    excerpt: str | None

    @field_validator("recorded_at")
    @classmethod
    def _recorded_at_with_timezone(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _with_utc(value)


class NoteSimilarity(BaseModel):
    """當日一筆護理過程紀錄與前日最相似紀錄的比對（相似度由模型估計）。"""

    record_id: str
    recorded_at: datetime
    similar_record_id: str | None
    similar_business_date: date | None
    similarity_percent: float | None
    issue_types: list[IssueType]

    @field_validator("recorded_at")
    @classmethod
    def _recorded_at_with_timezone(cls, value: datetime) -> datetime:
        return _with_utc(value)


class AuditFindingRead(BaseModel):
    """一筆稽核結果。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    audit_run_id: uuid.UUID
    rule_code: str
    patient_key: str
    business_date: date
    verdict: Verdict
    message: str
    evidence: list[Evidence]
    note_similarities: list[NoteSimilarity]
    engine: Engine
    model: str | None
    prompt_version: str | None
    system_prompt_version: int | None
    audited_at: datetime

    @field_validator("audited_at")
    @classmethod
    def _audited_at_with_timezone(cls, value: datetime) -> datetime:
        return _with_utc(value)


class AuditDayRead(BaseModel):
    """病患在一個業務日的稽核狀態。"""

    business_date: date
    admission_id: str
    auditable: bool
    not_auditable_reason: str | None
    latest_finding: AuditFindingRead | None


class AuditDaysRead(BaseModel):
    """病患所有有資料的業務日（由新到舊）。"""

    patient_key: str
    days: list[AuditDayRead]


class AuditRunCreate(BaseModel):
    """手動觸發一次稽核。"""

    patient_key: PatientKey
    business_date: date
    rule_code: Literal["R02"] = "R02"

    @field_validator("business_date", mode="before")
    @classmethod
    def _business_date_is_iso(cls, value: object) -> object:
        # 只接受 YYYY-MM-DD，不接受時間戳記等寬鬆格式
        if isinstance(value, str) and not _ISO_DATE_PATTERN.match(value):
            raise ValueError("業務日期格式必須為 YYYY-MM-DD")
        if isinstance(value, int | float):
            raise ValueError("業務日期格式必須為 YYYY-MM-DD")
        return value
