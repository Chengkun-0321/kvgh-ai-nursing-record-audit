"""唯一 LLM 出口：所有模型呼叫都經過這裡。

API 金鑰只在呼叫當下解密，不寫入 log、例外訊息或任何快取。
共用步驟（讀快照、組參數、錯誤訊息、ChatGPT 指示）在 `call_support`；結構化輸出在 `structured`。
"""

import logging
import time
import uuid
from collections.abc import Sequence
from typing import Any

import litellm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LlmProvider
from app.core.exceptions import LLMConnectionError
from app.schemas.llm_chat import ChatMessage
from app.services.llm import chatgpt_auth
from app.services.llm.call_support import (
    CHATGPT_INSTRUCTIONS_LOCK,
    LITELLM_ERRORS,
    PreparedCall,
    apply_chatgpt_instructions,
    describe_error,
    lookup_mode_for,
    prepare_call,
    prepend_system_prompt,
    read_call_snapshot,
)
from app.services.llm.chat_stream import ChatStream, StreamContext
from app.services.llm.structured import complete_structured
from app.services.llm.system_prompt_service import SystemPromptForCall

__all__ = ["LITELLM_ERRORS", "complete_structured", "lookup_model_mode", "open_chat_stream"]

logger = logging.getLogger(__name__)

# 不回報使用資料、不在錯誤時印出除錯提示（內網、避免輸出請求內容）
litellm.telemetry = False
litellm.suppress_debug_info = True


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
    snapshot = await read_call_snapshot(session, config_id)
    config = snapshot.config
    if config.provider == LlmProvider.CHATGPT:
        await chatgpt_auth.ensure_access_token()

    call = prepare_call(config, snapshot.system_prompt)
    started = time.perf_counter()
    try:
        stream = await _acompletion(call, messages, snapshot.system_prompt)
    except LITELLM_ERRORS as exc:
        logger.warning("測試對話無法開始：config_id=%s error=%s", config.id, type(exc).__name__)
        raise LLMConnectionError(describe_error(exc, call)) from exc

    # 只記版本號，不記 prompt 與對話內容
    logger.info(
        "測試對話開始：config_id=%s system_prompt_version=%s",
        config.id,
        call.system_prompt_version,
    )
    return ChatStream(stream, _stream_context(call, started))


async def _acompletion(
    call: PreparedCall, messages: Sequence[ChatMessage], system_prompt: SystemPromptForCall | None
) -> Any:
    """呼叫 LiteLLM 並回傳上游串流；ChatGPT 指示的互斥範圍只在這裡。

    LiteLLM 在 `litellm.acompletion` 完成之前（送出 HTTP 請求前）就會讀取
    `CHATGPT_DEFAULT_INSTRUCTIONS`（`litellm/llms/chatgpt/responses/transformation.py:79`，
    經 `common_utils.get_chatgpt_default_instructions` 以 `os.getenv` 讀取），而 `acompletion`
    在串流 HTTP 回應標頭到達後才回傳。因此鎖只需涵蓋到 `acompletion` 回傳為止，不會鎖住串流本身。
    """
    history = [message.model_dump(mode="json") for message in messages]
    request: dict[str, Any] = {
        "messages": prepend_system_prompt(history, system_prompt),
        "stream": True,
        "stream_options": {"include_usage": True},
        **call.kwargs,
    }
    if call.config.provider != LlmProvider.CHATGPT:
        return await litellm.acompletion(**request)
    async with CHATGPT_INSTRUCTIONS_LOCK:
        apply_chatgpt_instructions(system_prompt)
        return await litellm.acompletion(**request)


def _stream_context(call: PreparedCall, started: float) -> StreamContext:
    return StreamContext(
        config_id=call.config.id,
        litellm_model=call.litellm_model,
        system_prompt_version=call.system_prompt_version,
        started=started,
        errors=LITELLM_ERRORS,
        describe_error=lambda exc: describe_error(exc, call),
    )


def lookup_model_mode(provider: LlmProvider, model_id: str) -> str | None:
    """查 LiteLLM 價格表記載的模型模式（chat、responses、embedding…）；未收錄時為 `None`。"""
    return lookup_mode_for(provider, model_id)
