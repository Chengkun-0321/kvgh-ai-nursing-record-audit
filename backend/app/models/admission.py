"""病患的一次住院（去識別欄位）。"""

from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import PATIENT_KEY_MAX_LENGTH
from app.db.base import Base, IdMixin, TimestampMixin, UtcDateTime

_ID_MAX_LENGTH = 64
_SHORT_TEXT_MAX_LENGTH = 32
_DIAGNOSIS_MAX_LENGTH = 500


class Admission(IdMixin, TimestampMixin, Base):
    """一次住院；自然鍵 `admission_id`，每日資料包以最新內容覆蓋。"""

    __tablename__ = "admissions"

    patient_key: Mapped[str] = mapped_column(String(PATIENT_KEY_MAX_LENGTH), index=True)
    admission_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH), unique=True)
    bed_code: Mapped[str] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    sex: Mapped[str] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    age_years: Mapped[int] = mapped_column(Integer)
    admission_at: Mapped[datetime] = mapped_column(UtcDateTime)
    admission_source: Mapped[str] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    admission_diagnosis: Mapped[str] = mapped_column(String(_DIAGNOSIS_MAX_LENGTH))
    attending_physician_id: Mapped[str] = mapped_column(String(_ID_MAX_LENGTH))
    status: Mapped[str] = mapped_column(String(_SHORT_TEXT_MAX_LENGTH))
    status_changed_at: Mapped[datetime | None] = mapped_column(UtcDateTime)
