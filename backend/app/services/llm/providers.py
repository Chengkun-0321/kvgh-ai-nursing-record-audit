"""各服務類型對應的 LiteLLM 前綴與必填欄位（純資料與純函式，不 import litellm）。

前端 `frontend/src/lib/llmProviders.ts` 的欄位規則須與此處一致。
"""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final

from app.core.enums import LlmProvider
from app.core.exceptions import InvalidInputError


class FieldRequirement(StrEnum):
    """設定欄位在該服務類型是否需要。"""

    REQUIRED = "required"
    OPTIONAL = "optional"
    UNUSED = "unused"


@dataclass(frozen=True)
class ProviderSpec:
    """一種服務類型的呼叫方式。"""

    litellm_prefix: str
    api_key: FieldRequirement
    api_base: FieldRequirement
    default_api_base: str | None = None


OLLAMA_DEFAULT_API_BASE: Final = "http://localhost:11434"
# 本地 OpenAI 相容伺服器多半不驗證金鑰，但 LiteLLM 的 openai 路徑一定要帶一個值
LOCAL_SERVER_PLACEHOLDER_API_KEY: Final = "not-required"

PROVIDER_SPECS: Final = MappingProxyType(
    {
        LlmProvider.OPENAI: ProviderSpec(
            "openai", api_key=FieldRequirement.REQUIRED, api_base=FieldRequirement.UNUSED
        ),
        # 使用 ChatGPT 訂閱登入的 token，不需要 API 金鑰。
        # Codex 後端只接受 Responses API；LiteLLM 只對它內建清單上的模型自動改走 Responses，
        # 加上 `responses/` 讓新模型（例如 gpt-6 系列）也走 /responses，而不是 /chat/completions
        LlmProvider.CHATGPT: ProviderSpec(
            "chatgpt/responses",
            api_key=FieldRequirement.UNUSED,
            api_base=FieldRequirement.UNUSED,
        ),
        LlmProvider.GEMINI: ProviderSpec(
            "gemini", api_key=FieldRequirement.REQUIRED, api_base=FieldRequirement.UNUSED
        ),
        # ollama_chat 走 /api/chat，支援多輪對話格式
        LlmProvider.OLLAMA: ProviderSpec(
            "ollama_chat",
            api_key=FieldRequirement.UNUSED,
            api_base=FieldRequirement.OPTIONAL,
            default_api_base=OLLAMA_DEFAULT_API_BASE,
        ),
        LlmProvider.OPENAI_COMPATIBLE: ProviderSpec(
            "openai", api_key=FieldRequirement.OPTIONAL, api_base=FieldRequirement.REQUIRED
        ),
    }
)


def get_provider_spec(provider: LlmProvider) -> ProviderSpec:
    """取得服務類型的呼叫方式。"""
    return PROVIDER_SPECS[provider]


def build_litellm_model(provider: LlmProvider, model: str) -> str:
    """組成 LiteLLM 的 `prefix/model` 模型字串。"""
    return f"{get_provider_spec(provider).litellm_prefix}/{model}"


def resolve_api_base(provider: LlmProvider, api_base: str | None) -> str | None:
    """實際呼叫使用的 API 位址：未填時使用該服務類型的預設值。"""
    return api_base or get_provider_spec(provider).default_api_base


def check_required_fields(
    provider: LlmProvider, *, has_api_key: bool, api_base: str | None
) -> None:
    """檢查該服務類型的必填欄位。

    Raises:
        InvalidInputError: 缺少 API 金鑰或 API 位址。
    """
    spec = get_provider_spec(provider)
    if spec.api_key == FieldRequirement.REQUIRED and not has_api_key:
        raise InvalidInputError("此服務類型需要 API 金鑰")
    if spec.api_base == FieldRequirement.REQUIRED and not api_base:
        raise InvalidInputError("此服務類型需要 API 位址")
