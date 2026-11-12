"""模型設定的摘要文字：設定頁左欄（已儲存）與精靈最後一步（草稿）共用同一套描述。"""

from dataclasses import dataclass
from typing import Final

from app.core.enums import FieldRequirement, LlmProvider
from app.models.llm_config import LlmConfig
from app.schemas.llm_config import LlmConfigFields, LlmConfigRead
from app.schemas.llm_provider import SummaryRowRead
from app.services.llm.provider_catalog import NOT_REQUIRED, NOT_SET, api_base_row, provider_label
from app.services.llm.providers import get_provider_spec

_NEW_KEY: Final = "已輸入新的金鑰"


@dataclass(frozen=True)
class SummaryValues:
    """摘要各列要顯示的值（已轉成文字）。"""

    provider: LlmProvider
    api_base: str | None
    api_key: str
    model: str
    timeout: str


def to_config_read(config: LlmConfig) -> LlmConfigRead:
    """ORM 物件轉成回傳前端的設定，附服務名稱與摘要。"""
    fields = LlmConfigFields.model_validate(config)
    return LlmConfigRead(
        **fields.model_dump(exclude={"has_api_key"}),
        provider_label=provider_label(fields.provider),
        summary_rows=describe_saved_config(fields),
    )


def describe_saved_config(config: LlmConfigFields) -> list[SummaryRowRead]:
    """已儲存設定的摘要。"""
    uses_key = uses_api_key(config.provider)
    return summary_rows(
        SummaryValues(
            provider=config.provider,
            api_base=config.api_base,
            api_key=(config.api_key_hint or NOT_SET) if uses_key else NOT_REQUIRED,
            model=config.model,
            timeout=f"{config.timeout_seconds} 秒",
        )
    )


def describe_draft_api_key(
    provider: LlmProvider, *, typed_api_key: str, stored_key_hint: str | None
) -> str:
    """草稿的金鑰狀態；`stored_key_hint` 為可沿用的已儲存金鑰遮罩值。"""
    if not uses_api_key(provider):
        return NOT_REQUIRED
    if typed_api_key.strip():
        return _NEW_KEY
    return f"沿用已儲存的金鑰（{stored_key_hint}）" if stored_key_hint else NOT_SET


def describe_timeout(timeout_text: str, default_seconds: int) -> str:
    """草稿的逾時；未填時顯示後端預設值。"""
    stripped = timeout_text.strip()
    return f"{stripped} 秒" if stripped else f"預設 {default_seconds} 秒"


def summary_rows(values: SummaryValues) -> list[SummaryRowRead]:
    """依固定順序組出摘要列；用不到伺服器位址的服務類型不列位址。"""
    api_base_summary = api_base_row(values.provider, values.api_base)
    return [
        SummaryRowRead(label="服務類型", value=provider_label(values.provider)),
        *([api_base_summary] if api_base_summary else []),
        SummaryRowRead(label="API 金鑰", value=values.api_key),
        SummaryRowRead(label="模型", value=values.model or NOT_SET),
        SummaryRowRead(label="逾時", value=values.timeout),
    ]


def uses_api_key(provider: LlmProvider) -> bool:
    """該服務類型是否會用到 API 金鑰。"""
    return get_provider_spec(provider).api_key != FieldRequirement.UNUSED
