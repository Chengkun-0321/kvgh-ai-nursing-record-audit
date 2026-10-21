"""稽核批次與稽核結果。"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import PATIENT_KEY_MAX_LENGTH
from app.core.enums import Engine, Verdict
from app.db.base import Base, CreatedAtMixin, IdMixin, UtcDateTime

_RULE_CODE_MAX_LENGTH = 16
_MODEL_MAX_LENGTH = 255
_PROMPT_VERSION_MAX_LENGTH = 100
_ENUM_MAX_LENGTH = 16


class AuditRun(IdMixin, CreatedAtMixin, Base):
    """一次稽核執行（每次手動觸發一筆）。"""

    __tablename__ = "audit_runs"

    rule_code: Mapped[str] = mapped_column(String(_RULE_CODE_MAX_LENGTH))
    business_date: Mapped[date] = mapped_column(Date)
    patient_key: Mapped[str] = mapped_column(String(PATIENT_KEY_MAX_LENGTH), index=True)
    model: Mapped[str | None] = mapped_column(String(_MODEL_MAX_LENGTH))
    started_at: Mapped[datetime] = mapped_column(UtcDateTime)
    finished_at: Mapped[datetime] = mapped_column(UtcDateTime)


class AuditFinding(IdMixin, CreatedAtMixin, Base):
    """一位病患、一個業務日、一條規則的判定與 Evidence。"""

    __tablename__ = "audit_findings"

    audit_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("audit_runs.id"), index=True)
    rule_code: Mapped[str] = mapped_column(String(_RULE_CODE_MAX_LENGTH))
    patient_key: Mapped[str] = mapped_column(String(PATIENT_KEY_MAX_LENGTH), index=True)
    business_date: Mapped[date] = mapped_column(Date, index=True)
    verdict: Mapped[Verdict] = mapped_column(
        Enum(
            Verdict,
            native_enum=False,
            length=_ENUM_MAX_LENGTH,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    message: Mapped[str] = mapped_column(Text)
    # JSON 欄位（Any 為 DB 邊界）：結構由 schemas.audit 的 Evidence／NoteSimilarity 驗證
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    note_similarities: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    engine: Mapped[Engine] = mapped_column(
        Enum(
            Engine,
            native_enum=False,
            length=_ENUM_MAX_LENGTH,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    model: Mapped[str | None] = mapped_column(String(_MODEL_MAX_LENGTH))
    prompt_version: Mapped[str | None] = mapped_column(String(_PROMPT_VERSION_MAX_LENGTH))
    system_prompt_version: Mapped[int | None] = mapped_column(Integer)
    audited_at: Mapped[datetime] = mapped_column(UtcDateTime)
