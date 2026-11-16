"""LLM 呼叫的共用步驟：讀快照、組參數、錯誤訊息、ChatGPT 指示。

串流對話（`gateway.open_chat_stream`）與結構化輸出（`structured.complete_structured`）共用這些步驟。
本模組不開啟上游串流、也不決定呼叫方式；只有 gateway 與 structured 會呼叫 LiteLLM。
"""

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Any, Final

import litellm
from litellm import exceptions as litellm_errors
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import LlmProvider
from app.core.security import decrypt_secret
from app.services.llm import config_service, system_prompt_service
from app.services.llm import error_messages as messages
from app.services.llm.config_service import StoredLlmConfig
from app.services.llm.error_messages import ErrorCatalog, ErrorRule
from app.services.llm.providers import (
    LOCAL_SERVER_PLACEHOLDER_API_KEY,
    build_litellm_model,
    resolve_api_base,
)
from app.services.llm.system_prompt_service import SystemPromptForCall

# LiteLLM 會拋出的例外；涵蓋 litellm.LITELLM_EXCEPTION_TYPES（由測試確認升級後仍涵蓋）
LITELLM_ERRORS: Final[tuple[type[Exception], ...]] = (
    litellm_errors.AuthenticationError,
    litellm_errors.PermissionDeniedError,
    litellm_errors.NotFoundError,
    litellm_errors.BadRequestError,
    litellm_errors.UnprocessableEntityError,
    litellm_errors.RateLimitError,
    litellm_errors.Timeout,
    litellm_errors.APIConnectionError,
    litellm_errors.APIError,
    litellm_errors.InternalServerError,
    litellm_errors.ServiceUnavailableError,
    litellm_errors.BadGatewayError,
    litellm_errors.APIResponseValidationError,
    litellm_errors.OpenAIError,
)

# LiteLLM 每次呼叫 ChatGPT 訂閱時，從這個環境變數讀取要放在最前面的指示；未設定時用 Codex 內建指示
CHATGPT_BASE_INSTRUCTIONS_ENV_VAR: Final = "CHATGPT_DEFAULT_INSTRUCTIONS"

# 設定指示環境變數到 LiteLLM 讀取它之間，不可有其他 ChatGPT 呼叫插入（見 acompletion 呼叫處）
CHATGPT_INSTRUCTIONS_LOCK: Final = asyncio.Lock()


@dataclass(frozen=True)
class CallSnapshot:
    """DB 讀完後的不可變快照；之後的外部呼叫不再需要 session。"""

    config: StoredLlmConfig
    system_prompt: SystemPromptForCall | None


@dataclass(frozen=True)
class PreparedCall:
    """一次呼叫的參數；`kwargs` 不含訊息內容。"""

    config: StoredLlmConfig
    litellm_model: str
    kwargs: dict[str, Any]
    system_prompt_version: int | None


# LiteLLM 例外 → 訊息的對照；訊息與比對邏輯在 error_messages（該模組不 import litellm）。
# 順序有意義：子類別（Timeout、ContextWindowExceededError）必須排在父類別前面
ERROR_CATALOG: Final = ErrorCatalog(
    rules=(
        ErrorRule(litellm_errors.AuthenticationError, messages.describe_invalid_api_key),
        ErrorRule(litellm_errors.PermissionDeniedError, messages.describe_permission_denied),
        ErrorRule(litellm_errors.NotFoundError, messages.describe_model_not_found),
        ErrorRule(litellm_errors.RateLimitError, messages.describe_rate_limited),
        ErrorRule(litellm_errors.Timeout, messages.describe_timeout),
        ErrorRule(litellm_errors.APIConnectionError, messages.describe_connection_failure),
        ErrorRule(
            litellm_errors.InternalServerError,
            messages.describe_connection_failure,
            matches=messages.is_wrapped_connection_error,
        ),
        ErrorRule(
            litellm_errors.ContextWindowExceededError, messages.describe_context_window_exceeded
        ),
        ErrorRule(litellm_errors.ServiceUnavailableError, messages.describe_service_unavailable),
    ),
    bad_request_type=litellm_errors.BadRequestError,
)


async def read_call_snapshot(session: AsyncSession, config_id: uuid.UUID) -> CallSnapshot:
    """讀取設定與共用 system prompt，再結束交易釋放連線。

    必須在任何對外網路呼叫之前完成；本函式只讀取，`close()` 會回滾並歸還連線，
    session 之後若再被使用會重新取得連線。
    """
    config = await config_service.get_stored_config(session, config_id)
    system_prompt = await system_prompt_service.get_for_call(session)
    await session.close()
    return CallSnapshot(config=config, system_prompt=system_prompt)


def prepare_call(
    config: StoredLlmConfig, system_prompt: SystemPromptForCall | None
) -> PreparedCall:
    """組出 LiteLLM 參數（不含訊息）；共用的 timeout、drop_params、API 位址與金鑰。

    重試次數由呼叫端決定（`kwargs["num_retries"]`），這裡只給預設值。
    """
    litellm_model = build_litellm_model(config.provider, config.model)
    kwargs: dict[str, Any] = {
        "model": litellm_model,
        "timeout": config.timeout_seconds,
        "num_retries": get_settings().LLM_CHAT_NUM_RETRIES,
        "drop_params": True,
    }
    api_base = resolve_api_base(config.provider, config.api_base)
    if api_base:
        kwargs["api_base"] = api_base
    api_key = resolve_api_key(config)
    if api_key:
        kwargs["api_key"] = api_key
    return PreparedCall(
        config=config,
        litellm_model=litellm_model,
        kwargs=kwargs,
        system_prompt_version=system_prompt.version if system_prompt else None,
    )


def resolve_api_key(config: StoredLlmConfig) -> str | None:
    """只在呼叫當下解密金鑰；本地 OpenAI 相容伺服器沒有金鑰時給佔位值。"""
    if config.api_key_encrypted is not None:
        return decrypt_secret(config.api_key_encrypted)
    if config.provider == LlmProvider.OPENAI_COMPATIBLE:
        return LOCAL_SERVER_PLACEHOLDER_API_KEY
    return None


def describe_error(exc: Exception, call: PreparedCall) -> str:
    """模型服務例外 → 繁中訊息（遮蔽金鑰）。"""
    return messages.describe_error(exc, ERROR_CATALOG, call.config, call.kwargs.get("api_key"))


def system_prompt_content(system_prompt: SystemPromptForCall | None) -> str | None:
    """要送出的內容；從未設定或該版本已清空時為 `None`（不送 system 訊息）。"""
    if system_prompt is None or not system_prompt.content:
        return None
    return system_prompt.content


def prepend_system_prompt(
    history: list[dict[str, str]], system_prompt: SystemPromptForCall | None
) -> list[dict[str, str]]:
    """共用 system prompt 放在最前面；沒有內容時原樣回傳。"""
    content = system_prompt_content(system_prompt)
    if content is None:
        return history
    return [{"role": "system", "content": content}, *history]


def apply_chatgpt_instructions(system_prompt: SystemPromptForCall | None) -> None:
    """讓 ChatGPT 訂閱只送共用 system prompt，不再加上 Codex 內建指示。

    LiteLLM 會把環境變數的內容放在 instructions 最前面，但已包含在 instructions 內時不重複加入；
    因此設為與 system 訊息相同的內容，送出的 instructions 就只有共用 system prompt。
    共用 system prompt 為空時移除環境變數，改回 Codex 內建指示（Codex 後端需要 instructions）。
    這是整個程序共用的狀態，只能在 `CHATGPT_INSTRUCTIONS_LOCK` 內設定；
    併發的兩個請求若各自設定，會讓 LiteLLM 讀到別人的指示。
    由 test_gateway_concurrency 與 test_gateway_system_prompt 確認 LiteLLM 升級後行為不變。
    """
    content = system_prompt_content(system_prompt)
    if content is None:
        os.environ.pop(CHATGPT_BASE_INSTRUCTIONS_ENV_VAR, None)
        return
    os.environ[CHATGPT_BASE_INSTRUCTIONS_ENV_VAR] = content


def lookup_mode_for(provider: LlmProvider, model_id: str) -> str | None:
    """查 LiteLLM 價格表記載的模型模式；未收錄時為 `None`。"""
    prefixed = build_litellm_model(provider, model_id)
    info = litellm.model_cost.get(prefixed) or litellm.model_cost.get(model_id)
    mode = info.get("mode") if isinstance(info, dict) else None
    return mode if isinstance(mode, str) else None
