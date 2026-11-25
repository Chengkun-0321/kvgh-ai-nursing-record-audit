"""稽核執行紀錄：一列 `audit_runs` 代表某病患某日某規則的一次執行，發現存於 `audit_findings`。

重跑不覆蓋，每次新增一列；畫面顯示同一組條件下最新一列。不存 prompt 全文，只存輸入的 sha256。
"""

import uuid
from datetime import date
from enum import StrEnum
from typing import Final

from sqlalchemy import JSON, Date, Enum, Float, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AuditRunStatus, Verdict
from app.db.base import Base, CreatedAtMixin, IdMixin

_RULE_CODE_MAX_LENGTH: Final = 16
_PATIENT_KEY_MAX_LENGTH: Final = 32
_MODEL_MAX_LENGTH: Final = 200
_ITEM_MAX_LENGTH: Final = 200
_STATUS_MAX_LENGTH: Final = 32
_VERDICT_MAX_LENGTH: Final = 16
_DIGEST_LENGTH: Final = 64


def _enum_values(members: type[StrEnum]) -> list[str]:
    """Enum 以字串值存入資料庫（非原生 Enum，SQLite 與 PostgreSQL 皆相容）。"""
    return [member.value for member in members]


class AuditRun(IdMixin, CreatedAtMixin, Base):
    """一次稽核執行。`verdict` 只有 `COMPLETED` 才有值；其餘狀態以 `status_reason` 說明。"""

    __tablename__ = "audit_runs"
    __table_args__ = (
        Index("ix_audit_runs_patient_rule_date", "patient_key", "rule_code", "business_date"),
    )

    rule_code: Mapped[str] = mapped_column(String(_RULE_CODE_MAX_LENGTH))
    patient_key: Mapped[str] = mapped_column(String(_PATIENT_KEY_MAX_LENGTH))
    # 入院規則固定記在入院日；其他規則為畫面所選日期（見 service）
    business_date: Mapped[date] = mapped_column(Date)
    status: Mapped[AuditRunStatus] = mapped_column(
        Enum(
            AuditRunStatus,
            native_enum=False,
            length=_STATUS_MAX_LENGTH,
            values_callable=_enum_values,
        )
    )
    status_reason: Mapped[str | None] = mapped_column(Text)
    verdict: Mapped[Verdict | None] = mapped_column(
        Enum(Verdict, native_enum=False, length=_VERDICT_MAX_LENGTH, values_callable=_enum_values)
    )
    summary: Mapped[str | None] = mapped_column(Text)
    # 規則專屬欄位（共同輸出以外的部分）
    details: Mapped[dict[str, object] | None] = mapped_column(JSON)
    model: Mapped[str | None] = mapped_column(String(_MODEL_MAX_LENGTH))
    prompt_version: Mapped[int | None] = mapped_column(Integer)
    system_prompt_version: Mapped[int | None] = mapped_column(Integer)
    input_digest: Mapped[str | None] = mapped_column(String(_DIGEST_LENGTH))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    cost_usd: Mapped[float | None] = mapped_column(Float)
    duration_ms: Mapped[int | None] = mapped_column(Integer)

    findings: Mapped[list["AuditFinding"]] = relationship(
        back_populates="audit_run",
        cascade="all, delete-orphan",
        order_by="AuditFinding.position",
        lazy="raise",
    )


class AuditFinding(IdMixin, Base):
    """一次執行中的一個發現；`evidence` 為已通過原文核對的依據列表。"""

    __tablename__ = "audit_findings"

    audit_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    item: Mapped[str] = mapped_column(String(_ITEM_MAX_LENGTH))
    verdict: Mapped[Verdict] = mapped_column(
        Enum(Verdict, native_enum=False, length=_VERDICT_MAX_LENGTH, values_callable=_enum_values)
    )
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[dict[str, object]]] = mapped_column(JSON)

    audit_run: Mapped[AuditRun] = relationship(back_populates="findings", lazy="raise")
