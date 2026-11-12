"""設定頁的服務類型目錄：顯示名稱、說明、範例、精靈步驟、上限與設定摘要。

原本這些資料在前端各存一份、靠註解提醒「與後端一致」；改由後端提供後只剩一個來源。
欄位是否需要沿用 `providers.py` 的 `PROVIDER_SPECS`，這裡只補畫面用的文字。
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from app.core.config import get_settings
from app.core.constants import (
    CHAT_MAX_MESSAGE_CHARS,
    CHAT_MAX_MESSAGES,
    LLM_API_BASE_MAX_LENGTH,
    LLM_API_KEY_MAX_LENGTH,
    LLM_CONFIG_NAME_MAX_LENGTH,
    LLM_MODEL_MAX_LENGTH,
    LLM_SYSTEM_PROMPT_MAX_CHARS,
    LLM_TIMEOUT_MAX_SECONDS,
    LLM_TIMEOUT_MIN_SECONDS,
)
from app.core.enums import FieldRequirement, LlmProvider, ProviderChoice, WizardStepId
from app.schemas.llm_provider import (
    LlmProviderCatalogRead,
    LlmProviderOptionRead,
    LlmSettingLimitsRead,
    ProviderChoiceRead,
    SummaryRowRead,
    WizardStepRead,
)
from app.services.llm.providers import get_provider_spec

NOT_REQUIRED: Final = "不需要"
NOT_SET: Final = "未設定"
LOCAL_PROVIDERS: Final = frozenset({LlmProvider.OLLAMA, LlmProvider.OPENAI_COMPATIBLE})
# 選「本地模型」時先假設為 Ollama，實際類型由模型清單偵測後更新
_LOCAL_DEFAULT_PROVIDER: Final = LlmProvider.OLLAMA


@dataclass(frozen=True)
class _ProviderText:
    label: str
    description: str
    model_example: str
    api_base_example: str | None = None
    api_key_example: str | None = None


_PROVIDER_TEXTS: Final = MappingProxyType(
    {
        LlmProvider.OPENAI: _ProviderText(
            "Codex・API 金鑰",
            "使用 OpenAI Platform 的 API 金鑰，依用量計費",
            "gpt-5.3-codex",
            api_key_example="sk-…",
        ),
        LlmProvider.CHATGPT: _ProviderText(
            "Codex・ChatGPT 訂閱", "以 ChatGPT Plus／Pro 帳號登入，不需要 API 金鑰", "gpt-5.3-codex"
        ),
        LlmProvider.GEMINI: _ProviderText(
            "Gemini",
            "使用 Google AI Studio 的 API 金鑰",
            "gemini-3.5-flash",
            api_key_example="AIza…",
        ),
        LlmProvider.OLLAMA: _ProviderText(
            "本地模型（Ollama）", "連線到本機或院內的 Ollama 伺服器", "llama3.2"
        ),
        LlmProvider.OPENAI_COMPATIBLE: _ProviderText(
            "本地模型（OpenAI 相容）",
            "LM Studio、vLLM、llama.cpp 等提供 /v1 介面的伺服器",
            "qwen3-8b",
            api_base_example="http://localhost:1234/v1",
        ),
    }
)

# 第 1 步的選項順序：Codex、Gemini、本地模型
_CHOICES: Final = (
    ProviderChoiceRead(
        choice=ProviderChoice.OPENAI,
        label=_PROVIDER_TEXTS[LlmProvider.OPENAI].label,
        description=_PROVIDER_TEXTS[LlmProvider.OPENAI].description,
        default_provider=LlmProvider.OPENAI,
    ),
    ProviderChoiceRead(
        choice=ProviderChoice.CHATGPT,
        label=_PROVIDER_TEXTS[LlmProvider.CHATGPT].label,
        description=_PROVIDER_TEXTS[LlmProvider.CHATGPT].description,
        default_provider=LlmProvider.CHATGPT,
    ),
    ProviderChoiceRead(
        choice=ProviderChoice.GEMINI,
        label=_PROVIDER_TEXTS[LlmProvider.GEMINI].label,
        description=_PROVIDER_TEXTS[LlmProvider.GEMINI].description,
        default_provider=LlmProvider.GEMINI,
    ),
    ProviderChoiceRead(
        choice=ProviderChoice.LOCAL,
        label="本地模型",
        description="Ollama、LM Studio、vLLM 等本機或院內伺服器；系統自動判斷伺服器類型",
        default_provider=_LOCAL_DEFAULT_PROVIDER,
    ),
)

_WIZARD_STEPS: Final = (
    WizardStepRead(step_id=WizardStepId.PROVIDER, title="選擇服務類型"),
    WizardStepRead(step_id=WizardStepId.CONNECTION, title="連線設定"),
    WizardStepRead(step_id=WizardStepId.MODEL, title="選擇模型"),
    WizardStepRead(step_id=WizardStepId.DETAILS, title="命名與確認"),
)


def get_catalog() -> LlmProviderCatalogRead:
    """設定頁所需的服務類型目錄、精靈步驟與上限。"""
    return LlmProviderCatalogRead(
        providers=[provider_option(provider) for provider in LlmProvider],
        choices=list(_CHOICES),
        wizard_steps=list(_WIZARD_STEPS),
        limits=_limits(),
    )


def provider_option(provider: LlmProvider) -> LlmProviderOptionRead:
    """一種服務類型的顯示名稱與欄位規則。"""
    spec = get_provider_spec(provider)
    text = _PROVIDER_TEXTS[provider]
    return LlmProviderOptionRead(
        provider=provider,
        choice=to_provider_choice(provider),
        label=text.label,
        description=text.description,
        api_key=spec.api_key,
        api_base=spec.api_base,
        default_api_base=spec.default_api_base,
        api_base_example=text.api_base_example,
        api_key_example=text.api_key_example,
        model_example=text.model_example,
    )


def provider_label(provider: LlmProvider) -> str:
    """服務類型的顯示名稱。"""
    return _PROVIDER_TEXTS[provider].label


def to_provider_choice(provider: LlmProvider) -> ProviderChoice:
    """由儲存的服務類型推回畫面上的選項。"""
    if provider in LOCAL_PROVIDERS:
        return ProviderChoice.LOCAL
    return ProviderChoice(provider.value)


def api_base_row(provider: LlmProvider, api_base: str | None) -> SummaryRowRead | None:
    """摘要中的伺服器位址；該服務類型用不到位址時為 `None`。"""
    spec = get_provider_spec(provider)
    if spec.api_base == FieldRequirement.UNUSED:
        return None
    value = api_base or f"{spec.default_api_base or NOT_SET}（預設）"
    return SummaryRowRead(label="伺服器位址", value=value)


def _limits() -> LlmSettingLimitsRead:
    return LlmSettingLimitsRead(
        config_name_max_length=LLM_CONFIG_NAME_MAX_LENGTH,
        model_max_length=LLM_MODEL_MAX_LENGTH,
        api_base_max_length=LLM_API_BASE_MAX_LENGTH,
        api_key_max_length=LLM_API_KEY_MAX_LENGTH,
        timeout_min_seconds=LLM_TIMEOUT_MIN_SECONDS,
        timeout_max_seconds=LLM_TIMEOUT_MAX_SECONDS,
        default_timeout_seconds=get_settings().LLM_DEFAULT_TIMEOUT_SECONDS,
        timeout_hint=(
            f"{LLM_TIMEOUT_MIN_SECONDS}–{LLM_TIMEOUT_MAX_SECONDS} 秒，超過即視為失敗；"
            "本地模型較慢時可調高。"
        ),
        chat_max_messages=CHAT_MAX_MESSAGES,
        chat_max_message_chars=CHAT_MAX_MESSAGE_CHARS,
        # 一輪對話含使用者與模型各一則訊息
        chat_limit_reached_message=f"已達 {CHAT_MAX_MESSAGES // 2} 輪對話上限，請先清除對話。",
        system_prompt_max_chars=LLM_SYSTEM_PROMPT_MAX_CHARS,
    )
