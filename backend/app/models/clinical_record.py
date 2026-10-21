"""R02 需要的正規化紀錄：護理過程紀錄、生命徵象、檢驗結果、管路。

`business_date` 是該筆所屬資料包的業務日期（同一筆紀錄修改後重送時，以最新資料包為準）。
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import PATIENT_KEY_MAX_LENGTH
from app.db.base import Base, IdMixin, TimestampMixin, UtcDateTime

_ID_MAX_LENGTH = 64
_SHORT_TEXT_MAX_LENGTH = 64
_TEXT_MAX_LENGTH = 500


class _PatientDayMixin:
    """所有紀錄共用的病患、住院與資料包日期。"""

    patient_key: Mapped[str] = mapped_column(String(PATIENT_KEY_MAX_LENGTH), index=True)
    admission_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH), index=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)


class NursingProgressNote(IdMixin, TimestampMixin, _PatientDayMixin, Base):
    """護理過程紀錄；自然鍵 `record_id`。"""

    __tablename__ = "nursing_progress_notes"

    record_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH), unique=True)
    recorded_at: Mapped[datetime] = mapped_column(UtcDateTime)
    title_category: Mapped[str] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    title: Mapped[str] = mapped_column(String(_TEXT_MAX_LENGTH))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH))
    last_modified_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)


class VitalSign(IdMixin, TimestampMixin, _PatientDayMixin, Base):
    """生命徵象；自然鍵 `record_id`。"""

    __tablename__ = "vital_signs"

    record_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH), unique=True)
    measured_at: Mapped[datetime] = mapped_column(UtcDateTime)
    body_temperature: Mapped[float | None] = mapped_column(Float)
    temperature_site: Mapped[str | None] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    pulse: Mapped[int | None] = mapped_column(Integer)
    respiration: Mapped[int | None] = mapped_column(Integer)
    sbp: Mapped[int | None] = mapped_column(Integer)
    dbp: Mapped[int | None] = mapped_column(Integer)
    spo2: Mapped[int | None] = mapped_column(Integer)
    oxygen_therapy: Mapped[str | None] = mapped_column(String(_TEXT_MAX_LENGTH))
    measured_by: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH))


class LabResult(IdMixin, TimestampMixin, _PatientDayMixin, Base):
    """檢驗結果；自然鍵 `record_id`。"""

    __tablename__ = "lab_results"

    record_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH), unique=True)
    order_name: Mapped[str] = mapped_column(String(_TEXT_MAX_LENGTH))
    item: Mapped[str] = mapped_column(String(_TEXT_MAX_LENGTH))
    value: Mapped[str] = mapped_column(String(_TEXT_MAX_LENGTH))
    unit: Mapped[str | None] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    reference_range: Mapped[str | None] = mapped_column(String(_TEXT_MAX_LENGTH))
    abnormal_flag: Mapped[str | None] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    collected_at: Mapped[datetime] = mapped_column(UtcDateTime)
    reported_at: Mapped[datetime | None] = mapped_column(UtcDateTime)


class Tube(IdMixin, TimestampMixin, _PatientDayMixin, Base):
    """管路的每日現況；自然鍵 `(tube_id, business_date)`，保留每天的狀態供前後比較。"""

    __tablename__ = "tubes"
    __table_args__ = (UniqueConstraint("tube_id", "business_date"),)

    tube_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH))
    tube_type: Mapped[str] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    site: Mapped[str] = mapped_column(String(_TEXT_MAX_LENGTH))
    size: Mapped[str | None] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    inserted_on: Mapped[date | None] = mapped_column(Date)
    removed_on: Mapped[date | None] = mapped_column(Date)
    fixation: Mapped[str | None] = mapped_column(String(_TEXT_MAX_LENGTH))
    appearance: Mapped[str | None] = mapped_column(String(_TEXT_MAX_LENGTH))
