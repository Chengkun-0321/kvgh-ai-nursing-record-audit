"""使用者在網頁設定的 LLM 模型。"""

from sqlalchemy import Boolean, Enum, Index, Integer, String, Text, column, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import (
    LLM_API_BASE_MAX_LENGTH,
    LLM_API_KEY_HINT_MAX_LENGTH,
    LLM_CONFIG_NAME_MAX_LENGTH,
    LLM_MODEL_MAX_LENGTH,
)
from app.core.enums import LlmProvider
from app.db.base import Base, IdMixin, TimestampMixin

_PROVIDER_MAX_LENGTH = 32
# 只對使用中的列建立唯一索引：DB 層保證同一時間最多一組使用中（SQLite、PostgreSQL 皆支援）
_IS_ACTIVE_ONLY = column("is_active") == true()


class LlmConfig(IdMixin, TimestampMixin, Base):
    """一組模型設定；同一時間最多一筆 `is_active`（由部分唯一索引保證）。"""

    __tablename__ = "llm_configs"
    __table_args__ = (
        Index(
            "uq_llm_configs_is_active",
            "is_active",
            unique=True,
            sqlite_where=_IS_ACTIVE_ONLY,
            postgresql_where=_IS_ACTIVE_ONLY,
        ),
    )

    name: Mapped[str] = mapped_column(String(LLM_CONFIG_NAME_MAX_LENGTH), unique=True)
    provider: Mapped[LlmProvider] = mapped_column(
        Enum(
            LlmProvider,
            native_enum=False,
            length=_PROVIDER_MAX_LENGTH,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    # 不含 LiteLLM 前綴，前綴由 provider 決定
    model: Mapped[str] = mapped_column(String(LLM_MODEL_MAX_LENGTH))
    api_base: Mapped[str | None] = mapped_column(String(LLM_API_BASE_MAX_LENGTH))
    # Fernet 加密後的 key；明文不落地
    api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    # 遮罩值（sk-…abcd），列表顯示不必解密
    api_key_hint: Mapped[str | None] = mapped_column(String(LLM_API_KEY_HINT_MAX_LENGTH))
    timeout_seconds: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
