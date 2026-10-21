"""唯一 LLM 出口：所有模型呼叫都經過這裡。

API 金鑰只在呼叫當下解密，不寫入 log、例外訊息或任何快取。
"""

import logging
import os
import re
import time
import uuid
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Final

import litellm
from litellm import exceptions as litellm_errors
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import LlmProvider
from app.core.exceptions import (
    LLMConnectionError,
    LLMNotConfiguredError,
    LLMOutputError,
    LLMServiceError,
    LLMTimeoutError,
)
from app.core.security import decrypt_secret
from app.crud import llm_config as llm_config_crud
from app.db.session import get_session_factory
from app.schemas.llm_chat import ChatDeltaEvent, ChatDoneEvent, ChatErrorEvent, ChatMessage
from app.schemas.llm_structured import LLMRequest, LLMResult
from app.services.llm import chatgpt_auth, config_service, system_prompt_service
from app.services.llm.config_service import StoredLlmConfig
from app.services.llm.prompt_loader import prompt_id, render_prompt
from app.services.llm.providers import (
    LOCAL_SERVER_PLACEHOLDER_API_KEY,
    build_litellm_model,
    resolve_api_base,
)
from app.services.llm.redaction import redact_provider_detail
from app.services.llm.system_prompt_service import SystemPromptForCall

__all__ = [
    "LITELLM_ERRORS",
    "ActiveModelSettings",
    "LLMOutputError",
    "complete_structured",
    "load_active_model_settings",
    "lookup_model_mode",
    "open_chat_stream",
]

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


# ---- 結構化呼叫（稽核規則使用）----

_JSON_FENCE_PATTERN: Final = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)
_RETRY_INSTRUCTION: Final = "上一個回覆不符合要求的 JSON 格式，請修正下列問題後，只回傳 JSON："
# 成本只是附加資訊：LiteLLM 對價格表未收錄的模型會拋出一般 Exception，取不到就記為 None，
# 不讓整次稽核失敗
_COST_ERRORS: Final[tuple[type[Exception], ...]] = (Exception,)


@dataclass(frozen=True)
class ActiveModelSettings:
    """結構化呼叫使用的模型設定；`api_key` 為呼叫當下才解密的明文，不可寫入 log 或快取。"""

    provider: str
    # LiteLLM 完整模型名稱，例：`openai/gpt-4.1`
    model: str
    api_key: str | None
    api_base: str | None
    timeout_seconds: float
    # 共用 system prompt；空字串表示不使用
    system_prompt: str
    system_prompt_version: int | None


async def load_active_model_settings() -> ActiveModelSettings:
    """讀取使用中的模型設定（解密金鑰）與最新的共用 system prompt。

    Raises:
        LLMNotConfiguredError: 尚未設定使用中的模型。
        ChatgptAuthRequiredError: ChatGPT 訂閱尚未登入。
    """
    async with get_session_factory()() as session:
        active = await llm_config_crud.get_active(session)
        if active is None:
            raise LLMNotConfiguredError
        config = await config_service.get_stored_config(session, active.id)
        system_prompt = await system_prompt_service.get_for_call(session)
    if config.provider == LlmProvider.CHATGPT:
        await chatgpt_auth.ensure_access_token()
    return ActiveModelSettings(
        provider=config.provider.value,
        model=build_litellm_model(config.provider, config.model),
        api_key=_resolve_api_key(config),
        api_base=resolve_api_base(config.provider, config.api_base),
        timeout_seconds=float(config.timeout_seconds),
        system_prompt=_system_prompt_content(system_prompt) or "",
        system_prompt_version=system_prompt.version if system_prompt else None,
    )


async def complete_structured[T: BaseModel](
    request: LLMRequest, output_schema: type[T]
) -> LLMResult[T]:
    """以使用中的模型執行規則 prompt，並以 `output_schema` 驗證輸出。

    訊息依序為共用 system prompt（有內容時）與規則 prompt；輸出不符格式時附上驗證錯誤重試，
    最多 `LLM_MAX_RETRIES` 次。

    Args:
        request: 規則代碼、prompt 名稱與版本、模板變數。
        output_schema: 期望輸出的 Pydantic model。

    Returns:
        驗證後的輸出與模型、prompt 版本、token 用量、成本、耗時。

    Raises:
        LLMNotConfiguredError: 尚未設定使用中的模型。
        LLMOutputError: 重試用盡仍不符格式。
        LLMTimeoutError: 呼叫逾時（`TimeoutError` 子類別）。
        LLMServiceError: 連線失敗或服務錯誤（`ConnectionError` 子類別）。
    """
    settings = await load_active_model_settings()
    messages = _preprocess(_structured_messages(settings, request))
    if settings.provider == LlmProvider.CHATGPT:
        _apply_chatgpt_instructions(
            SystemPromptForCall(
                version=settings.system_prompt_version or 0, content=settings.system_prompt
            )
        )
    started = time.perf_counter()
    parsed, response = await _complete_and_validate(settings, messages, output_schema)
    usage = getattr(response, "usage", None)
    # 只記規則代碼與版本，不記 prompt 與輸出內容
    logger.info(
        "結構化呼叫完成：rule_code=%s prompt=%s system_prompt_version=%s",
        request.rule_code,
        prompt_id(request.prompt_name, request.prompt_version),
        settings.system_prompt_version,
    )
    return LLMResult(
        parsed=parsed,
        model=_litellm_model_name(settings),
        prompt_version=prompt_id(request.prompt_name, request.prompt_version),
        system_prompt_version=settings.system_prompt_version,
        prompt_tokens=_int_or_none(getattr(usage, "prompt_tokens", None)),
        completion_tokens=_int_or_none(getattr(usage, "completion_tokens", None)),
        cost_usd=_completion_cost(response),
        duration_ms=_elapsed_ms(started, time.perf_counter()),
    )


def _structured_messages(
    settings: ActiveModelSettings, request: LLMRequest
) -> list[dict[str, str]]:
    prompt = render_prompt(request.prompt_name, request.prompt_version, request.variables)
    user_message = {"role": "user", "content": prompt}
    if not settings.system_prompt:
        return [user_message]
    return [{"role": "system", "content": settings.system_prompt}, user_message]


def _preprocess(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """送出前的處理點；目前原樣送出，接真實資料時在此插入去識別化（ADR 0002）。"""
    return messages


async def _complete_and_validate[T: BaseModel](
    settings: ActiveModelSettings, messages: list[dict[str, str]], output_schema: type[T]
) -> tuple[T, Any]:
    conversation = list(messages)
    max_attempts = 1 + max(get_settings().LLM_MAX_RETRIES, 0)
    for attempt in range(1, max_attempts + 1):
        response = await _acompletion(settings, conversation)
        content = _response_content(response)
        try:
            return output_schema.model_validate_json(_strip_json_fence(content)), response
        except ValidationError as exc:
            logger.warning(
                "模型輸出不符格式：attempt=%d/%d errors=%d",
                attempt,
                max_attempts,
                exc.error_count(),
            )
            conversation = [
                *conversation,
                {"role": "assistant", "content": content},
                {"role": "user", "content": _retry_instruction(exc)},
            ]
    raise LLMOutputError


def _litellm_model_name(settings: ActiveModelSettings) -> str:
    """送出與回傳共用的 LiteLLM 完整模型名稱（`<provider>/<model>`）。

    `settings.model` 已含 `/` 時原樣使用；否則依服務類型補上 LiteLLM 前綴。
    """
    if "/" in settings.model:
        return settings.model
    try:
        provider = LlmProvider(settings.provider)
    except ValueError:
        return f"{settings.provider}/{settings.model}"
    return build_litellm_model(provider, settings.model)


async def _acompletion(settings: ActiveModelSettings, messages: list[dict[str, str]]) -> Any:
    """呼叫 LiteLLM；逾時與服務錯誤轉成標準例外，gateway 以外不必認識 LiteLLM 的例外。"""
    model_name = _litellm_model_name(settings)
    kwargs: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "temperature": 0,
        "timeout": settings.timeout_seconds,
        "drop_params": True,
    }
    if settings.api_key:
        kwargs["api_key"] = settings.api_key
    if settings.api_base:
        kwargs["api_base"] = settings.api_base
    try:
        return await litellm.acompletion(**kwargs)
    except litellm_errors.Timeout as exc:
        logger.warning("模型呼叫逾時：model=%s", model_name)
        raise LLMTimeoutError("模型回應逾時") from exc
    except LITELLM_ERRORS as exc:
        logger.warning("模型服務呼叫失敗：model=%s error=%s", model_name, type(exc).__name__)
        raise LLMServiceError("無法連線到模型服務或服務回應錯誤") from exc


def _response_content(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if not choices:
        return ""
    content = getattr(getattr(choices[0], "message", None), "content", None)
    return content if isinstance(content, str) else ""


def _strip_json_fence(content: str) -> str:
    """去除 ```json 程式碼區塊標記。"""
    match = _JSON_FENCE_PATTERN.match(content)
    return match.group(1) if match else content.strip()


def _retry_instruction(exc: ValidationError) -> str:
    """把驗證錯誤整理成給模型的修正說明；不附上輸入值。"""
    details = [
        f"- {'.'.join(str(part) for part in error['loc']) or '整體'}：{error['msg']}"
        for error in exc.errors(include_url=False, include_context=False, include_input=False)
    ]
    return "\n".join([_RETRY_INSTRUCTION, *details])


def _completion_cost(response: Any) -> float | None:
    try:
        cost = litellm.completion_cost(completion_response=response)
    except _COST_ERRORS as exc:
        logger.warning("無法計算模型呼叫成本：error=%s", type(exc).__name__)
        return None
    return float(cost) if isinstance(cost, int | float) else None


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
