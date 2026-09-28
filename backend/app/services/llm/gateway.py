"""唯一 LLM 出口：所有模型呼叫都經過這裡。

API 金鑰只在呼叫當下解密，不寫入 log、例外訊息或任何快取。
"""

import logging
import os
import time
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final

import litellm
from litellm import exceptions as litellm_errors
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import LlmProvider
from app.core.exceptions import LLMConnectionError
from app.core.security import decrypt_secret
from app.schemas.llm_chat import ChatDeltaEvent, ChatDoneEvent, ChatErrorEvent, ChatMessage
from app.services.llm import chatgpt_auth, config_service, system_prompt_service
from app.services.llm.config_service import StoredLlmConfig
from app.services.llm.providers import (
    LOCAL_SERVER_PLACEHOLDER_API_KEY,
    build_litellm_model,
    resolve_api_base,
)
from app.services.llm.redaction import redact_provider_detail
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

ChatStreamItem = ChatDeltaEvent | ChatDoneEvent | ChatErrorEvent


@dataclass(frozen=True)
class _PreparedCall:
    config: StoredLlmConfig
    litellm_model: str
    kwargs: dict[str, Any]
    system_prompt_version: int | None


@dataclass(frozen=True)
class _ErrorRule:
    error_type: type[Exception]
    describe: Callable[[StoredLlmConfig], str]
    matches: Callable[[Exception], bool] = lambda _: True


def _describe_connection_failure(config: StoredLlmConfig) -> str:
    target = resolve_api_base(config.provider, config.api_base) or "模型服務"
    return f"無法連線到 {target}，請確認伺服器已啟動且位址正確"


def _is_wrapped_connection_error(exc: Exception) -> bool:
    # LiteLLM 的 openai 路徑把連線失敗包成 InternalServerError（訊息為 "Connection error."）
    return "connection error" in str(getattr(exc, "message", "")).lower()


# 順序有意義：子類別（Timeout、ContextWindowExceededError）必須排在父類別前面
_ERROR_RULES: Final = (
    _ErrorRule(litellm_errors.AuthenticationError, lambda _: "API 金鑰無效或已過期，請確認金鑰"),
    _ErrorRule(
        litellm_errors.PermissionDeniedError,
        lambda _: "此金鑰沒有使用該模型的權限，請確認帳戶或專案設定",
    ),
    _ErrorRule(
        litellm_errors.NotFoundError, lambda config: f"找不到模型「{config.model}」，請確認模型名稱"
    ),
    _ErrorRule(
        litellm_errors.RateLimitError,
        lambda _: "已達服務的速率或額度上限，請稍後再試或確認帳戶額度",
    ),
    _ErrorRule(
        litellm_errors.Timeout,
        lambda config: f"超過 {config.timeout_seconds} 秒沒有回應，請確認服務狀態或調高逾時秒數",
    ),
    _ErrorRule(litellm_errors.APIConnectionError, _describe_connection_failure),
    _ErrorRule(
        litellm_errors.InternalServerError,
        _describe_connection_failure,
        matches=_is_wrapped_connection_error,
    ),
    _ErrorRule(
        litellm_errors.ContextWindowExceededError,
        lambda _: "對話內容超過模型可處理的長度，請清除對話後再試",
    ),
    _ErrorRule(
        litellm_errors.ServiceUnavailableError, lambda _: "模型服務暫時無法使用，請稍後再試"
    ),
)


async def open_chat_stream(
    session: AsyncSession, config_id: uuid.UUID, messages: Sequence[ChatMessage]
) -> AsyncIterator[ChatStreamItem]:
    """以指定設定開啟測試對話串流。

    先建立連線再回傳串流：金鑰無效、找不到模型等錯誤會在回應開始前以 HTTP 錯誤回報；
    串流途中的錯誤則轉成 `error` 事件。

    Args:
        session: DB session。
        config_id: 要測試的模型設定。
        messages: 完整對話歷史，最後一則為使用者訊息。

    Returns:
        依序產生 `delta`、最後 `done`（或 `error`）事件的串流。

    Raises:
        NotFoundError: 查無設定。
        ChatgptAuthRequiredError: ChatGPT 訂閱尚未登入。
        LLMConnectionError: 無法開啟串流。
    """
    config = await config_service.get_stored_config(session, config_id)
    system_prompt = await system_prompt_service.get_for_call(session)
    if config.provider == LlmProvider.CHATGPT:
        await chatgpt_auth.ensure_access_token()
        _apply_chatgpt_instructions(system_prompt)

    call = _prepare_call(config, system_prompt)
    started = time.perf_counter()
    try:
        stream = await litellm.acompletion(
            messages=_build_messages(messages, system_prompt),
            stream=True,
            stream_options={"include_usage": True},
            **call.kwargs,
        )
    except LITELLM_ERRORS as exc:
        logger.warning("測試對話無法開始：config_id=%s error=%s", config.id, type(exc).__name__)
        raise LLMConnectionError(_describe_error(exc, call)) from exc

    # 只記版本號，不記 prompt 與對話內容
    logger.info(
        "測試對話開始：config_id=%s system_prompt_version=%s",
        config.id,
        call.system_prompt_version,
    )
    return _relay_stream(stream, call, started)


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
    這是整個程序共用的狀態，只在這裡設定；由 test_gateway 確認 LiteLLM 升級後行為不變。
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


async def _relay_stream(
    stream: Any, call: _PreparedCall, started: float
) -> AsyncIterator[ChatStreamItem]:
    first_token_at: float | None = None
    usage: Any = None
    try:
        async for chunk in stream:
            text = _chunk_text(chunk)
            if text:
                first_token_at = first_token_at or time.perf_counter()
                yield ChatDeltaEvent(type="delta", text=text)
            usage = getattr(chunk, "usage", None) or usage
    except LITELLM_ERRORS as exc:
        logger.warning(
            "測試對話串流中斷：config_id=%s error=%s", call.config.id, type(exc).__name__
        )
        yield ChatErrorEvent(type="error", message=_describe_error(exc, call))
        return

    yield ChatDoneEvent(
        type="done",
        model=call.litellm_model,
        latency_ms=_elapsed_ms(started, time.perf_counter()),
        first_token_ms=_elapsed_ms(started, first_token_at) if first_token_at else None,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        system_prompt_version=call.system_prompt_version,
    )


def _chunk_text(chunk: Any) -> str | None:
    choices = getattr(chunk, "choices", None)
    if not choices:
        return None
    content = getattr(choices[0].delta, "content", None)
    return content if isinstance(content, str) else None


def _elapsed_ms(started: float, ended: float) -> int:
    return round((ended - started) * 1000)


def _describe_error(exc: Exception, call: _PreparedCall) -> str:
    """把 LiteLLM 例外轉成可操作的繁中訊息；不回傳原始例外字串，只附遮蔽後的服務說明。"""
    for rule in _ERROR_RULES:
        if isinstance(exc, rule.error_type) and rule.matches(exc):
            return rule.describe(call.config)
    detail = redact_provider_detail(
        str(getattr(exc, "message", "") or ""), call.kwargs.get("api_key")
    )
    base = "服務拒絕此請求，請確認模型名稱與設定"
    if not isinstance(exc, litellm_errors.BadRequestError):
        base = "模型服務回應錯誤，請稍後再試"
    return f"{base}（{detail}）" if detail else base


def lookup_model_mode(provider: LlmProvider, model_id: str) -> str | None:
    """查 LiteLLM 價格表記載的模型模式（chat、responses、embedding…）；未收錄時為 `None`。"""
    prefixed = build_litellm_model(provider, model_id)
    info = litellm.model_cost.get(prefixed) or litellm.model_cost.get(model_id)
    mode = info.get("mode") if isinstance(info, dict) else None
    return mode if isinstance(mode, str) else None
