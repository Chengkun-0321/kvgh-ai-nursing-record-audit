"""唯一 LLM 出口：所有模型呼叫都經過這裡。

API 金鑰只在呼叫當下解密，不寫入 log、例外訊息或任何快取。
"""

import asyncio
import logging
import os
import time
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

import litellm
from litellm import exceptions as litellm_errors
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import LlmProvider
from app.core.exceptions import LLMConnectionError
from app.core.security import decrypt_secret
from app.schemas.llm_chat import ChatMessage
from app.services.llm import chatgpt_auth, config_service, system_prompt_service
from app.services.llm import error_messages as messages
from app.services.llm.chat_stream import ChatStream, StreamContext
from app.services.llm.config_service import StoredLlmConfig
from app.services.llm.error_messages import ErrorCatalog, ErrorRule
from app.services.llm.providers import (
    LOCAL_SERVER_PLACEHOLDER_API_KEY,
    build_litellm_model,
    resolve_api_base,
)
from app.services.llm.system_prompt_service import SystemPromptForCall

logger = logging.getLogger(__name__)

# 不回報使用資料、不在錯誤時印出除錯提示（內網、避免輸出請求內容）
litellm.telemetry = False
litellm.suppress_debug_info = True

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
_CHATGPT_BASE_INSTRUCTIONS_ENV_VAR: Final = "CHATGPT_DEFAULT_INSTRUCTIONS"

# 設定 ChatGPT 指示環境變數到 LiteLLM 讀取它之間，不可有其他 ChatGPT 呼叫插入（見 _acompletion）
_CHATGPT_INSTRUCTIONS_LOCK: Final = asyncio.Lock()


@dataclass(frozen=True)
class _CallSnapshot:
    """DB 讀完後的不可變快照；之後的外部呼叫不再需要 session。"""

    config: StoredLlmConfig
    system_prompt: SystemPromptForCall | None


@dataclass(frozen=True)
class _PreparedCall:
    config: StoredLlmConfig
    litellm_model: str
    kwargs: dict[str, Any]
    system_prompt_version: int | None


# LiteLLM 例外 → 訊息的對照；訊息與比對邏輯在 error_messages（該模組不 import litellm）。
# 順序有意義：子類別（Timeout、ContextWindowExceededError）必須排在父類別前面
_ERROR_CATALOG: Final = ErrorCatalog(
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


async def open_chat_stream(
    session: AsyncSession, config_id: uuid.UUID, messages: Sequence[ChatMessage]
) -> ChatStream:
    """以指定設定開啟測試對話串流。

    先建立連線再回傳串流：金鑰無效、找不到模型等錯誤會在回應開始前以 HTTP 錯誤回報；
    串流途中的錯誤則轉成 `error` 事件。

    DB 只用來讀取快照，讀完即結束交易、歸還連線；之後的 ChatGPT 換發與模型串流都不占用連線池。

    Args:
        session: DB session；本函式讀完後會結束其交易，呼叫端之後不應再用它查詢。
        config_id: 要測試的模型設定。
        messages: 完整對話歷史，最後一則為使用者訊息。

    Returns:
        依序產生 `delta`、最後 `done`（或 `error`）事件的串流。上游此時已開啟，
        呼叫端必須在結束時 `aclose()`（即使從未迭代），否則上游要等垃圾回收才關閉。

    Raises:
        NotFoundError: 查無設定。
        ChatgptAuthRequiredError: ChatGPT 訂閱尚未登入。
        LLMConnectionError: 無法開啟串流。
    """
    snapshot = await _read_call_snapshot(session, config_id)
    config = snapshot.config
    if config.provider == LlmProvider.CHATGPT:
        await chatgpt_auth.ensure_access_token()

    call = _prepare_call(config, snapshot.system_prompt)
    started = time.perf_counter()
    try:
        stream = await _acompletion(call, messages, snapshot.system_prompt)
    except LITELLM_ERRORS as exc:
        logger.warning("測試對話無法開始：config_id=%s error=%s", config.id, type(exc).__name__)
        raise LLMConnectionError(_describe_error(exc, call)) from exc

    # 只記版本號，不記 prompt 與對話內容
    logger.info(
        "測試對話開始：config_id=%s system_prompt_version=%s",
        config.id,
        call.system_prompt_version,
    )
    return ChatStream(stream, _stream_context(call, started))


async def _read_call_snapshot(session: AsyncSession, config_id: uuid.UUID) -> _CallSnapshot:
    """讀取設定與共用 system prompt，再結束交易釋放連線。

    必須在任何對外網路呼叫之前完成；本函式只讀取，`close()` 會回滾並歸還連線，
    session 之後若再被使用會重新取得連線。
    """
    config = await config_service.get_stored_config(session, config_id)
    system_prompt = await system_prompt_service.get_for_call(session)
    await session.close()
    return _CallSnapshot(config=config, system_prompt=system_prompt)


async def _acompletion(
    call: _PreparedCall, messages: Sequence[ChatMessage], system_prompt: SystemPromptForCall | None
) -> Any:
    """呼叫 LiteLLM 並回傳上游串流；ChatGPT 指示的互斥範圍只在這裡。

    LiteLLM 在 `litellm.acompletion` 完成之前（送出 HTTP 請求前）就會讀取
    `CHATGPT_DEFAULT_INSTRUCTIONS`（`litellm/llms/chatgpt/responses/transformation.py:79`，
    經 `common_utils.get_chatgpt_default_instructions` 以 `os.getenv` 讀取），而 `acompletion`
    在串流 HTTP 回應標頭到達後才回傳。因此鎖只需涵蓋到 `acompletion` 回傳為止，不會鎖住串流本身。
    """
    request: dict[str, Any] = {
        "messages": _build_messages(messages, system_prompt),
        "stream": True,
        "stream_options": {"include_usage": True},
        **call.kwargs,
    }
    if call.config.provider != LlmProvider.CHATGPT:
        return await litellm.acompletion(**request)
    async with _CHATGPT_INSTRUCTIONS_LOCK:
        _apply_chatgpt_instructions(system_prompt)
        return await litellm.acompletion(**request)


def _build_messages(
    messages: Sequence[ChatMessage], system_prompt: SystemPromptForCall | None
) -> list[dict[str, str]]:
    """共用 system prompt 放在最前面；LiteLLM 會依服務轉成各自的格式（instructions 等）。"""
    history = [message.model_dump(mode="json") for message in messages]
    content = _system_prompt_content(system_prompt)
    if content is None:
        return history
    return [{"role": "system", "content": content}, *history]


def _apply_chatgpt_instructions(system_prompt: SystemPromptForCall | None) -> None:
    """讓 ChatGPT 訂閱只送共用 system prompt，不再加上 Codex 內建指示。

    LiteLLM 會把環境變數的內容放在 instructions 最前面，但已包含在 instructions 內時不重複加入；
    因此設為與 system 訊息相同的內容，送出的 instructions 就只有共用 system prompt。
    共用 system prompt 為空時移除環境變數，改回 Codex 內建指示（Codex 後端需要 instructions）。
    這是整個程序共用的狀態，只能由 `_acompletion` 在 `_CHATGPT_INSTRUCTIONS_LOCK` 內設定；
    併發的兩個請求若各自設定，會讓 LiteLLM 讀到別人的指示。
    由 test_gateway_concurrency 與 test_gateway_system_prompt 確認 LiteLLM 升級後行為不變。
    """
    content = _system_prompt_content(system_prompt)
    if content is None:
        os.environ.pop(_CHATGPT_BASE_INSTRUCTIONS_ENV_VAR, None)
        return
    os.environ[_CHATGPT_BASE_INSTRUCTIONS_ENV_VAR] = content


def _system_prompt_content(system_prompt: SystemPromptForCall | None) -> str | None:
    """要送出的內容；從未設定或該版本已清空時為 `None`（不送 system 訊息）。"""
    if system_prompt is None or not system_prompt.content:
        return None
    return system_prompt.content


def _prepare_call(
    config: StoredLlmConfig, system_prompt: SystemPromptForCall | None
) -> _PreparedCall:
    litellm_model = build_litellm_model(config.provider, config.model)
    # 測試對話不帶 temperature：部分 Codex 模型只接受預設值；其餘不支援的參數由 drop_params 移除
    kwargs: dict[str, Any] = {
        "model": litellm_model,
        "timeout": config.timeout_seconds,
        "num_retries": get_settings().LLM_CHAT_NUM_RETRIES,
        "drop_params": True,
    }
    api_base = resolve_api_base(config.provider, config.api_base)
    if api_base:
        kwargs["api_base"] = api_base
    api_key = _resolve_api_key(config)
    if api_key:
        kwargs["api_key"] = api_key
    return _PreparedCall(
        config=config,
        litellm_model=litellm_model,
        kwargs=kwargs,
        system_prompt_version=system_prompt.version if system_prompt else None,
    )


def _resolve_api_key(config: StoredLlmConfig) -> str | None:
    if config.api_key_encrypted is not None:
        return decrypt_secret(config.api_key_encrypted)
    if config.provider == LlmProvider.OPENAI_COMPATIBLE:
        return LOCAL_SERVER_PLACEHOLDER_API_KEY
    return None


def _stream_context(call: _PreparedCall, started: float) -> StreamContext:
    return StreamContext(
        config_id=call.config.id,
        litellm_model=call.litellm_model,
        system_prompt_version=call.system_prompt_version,
        started=started,
        errors=LITELLM_ERRORS,
        describe_error=lambda exc: _describe_error(exc, call),
    )


def _describe_error(exc: Exception, call: _PreparedCall) -> str:
    return messages.describe_error(exc, _ERROR_CATALOG, call.config, call.kwargs.get("api_key"))


def lookup_model_mode(provider: LlmProvider, model_id: str) -> str | None:
    """查 LiteLLM 價格表記載的模型模式（chat、responses、embedding…）；未收錄時為 `None`。"""
    prefixed = build_litellm_model(provider, model_id)
    info = litellm.model_cost.get(prefixed) or litellm.model_cost.get(model_id)
    mode = info.get("mode") if isinstance(info, dict) else None
    return mode if isinstance(mode, str) else None
