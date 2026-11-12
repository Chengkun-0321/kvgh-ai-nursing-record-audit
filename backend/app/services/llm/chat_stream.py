"""測試對話串流：把上游模型串流轉成 `delta`／`done`／`error` 事件，並確定性地關閉上游。

本模組不 import litellm（llm.md：只有 gateway 可 import）：要攔截的例外類別與錯誤訊息
由 gateway 以 `StreamContext` 傳入。
"""

import inspect
import logging
import time
import uuid
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass
from typing import Any

from app.schemas.llm_chat import ChatDeltaEvent, ChatDoneEvent, ChatErrorEvent

logger = logging.getLogger(__name__)

ChatStreamItem = ChatDeltaEvent | ChatDoneEvent | ChatErrorEvent


@dataclass(frozen=True)
class StreamContext:
    """轉送串流所需、由 gateway 準備好的資訊。

    Attributes:
        config_id: 模型設定 ID（只用於 log）。
        litellm_model: `done` 事件回報的模型名稱。
        system_prompt_version: `done` 事件回報的共用 system prompt 版本。
        started: 開始呼叫的時間（`time.perf_counter()`），用來計算延遲。
        errors: 串流途中要轉成 `error` 事件的例外類別。
        describe_error: 例外 → 繁中訊息。
    """

    config_id: uuid.UUID
    litellm_model: str
    system_prompt_version: int | None
    started: float
    errors: tuple[type[Exception], ...]
    describe_error: Callable[[Exception], str]


class ChatStream:
    """測試對話的事件串流；上游一定會被關閉，且只關閉一次。

    async generator 在開始迭代前被 `aclose()` 時不會執行其 `finally`，因此不能只靠 relay 的
    `finally` 關閉上游：回應開始前就取消、從未被迭代的串流，要由 `aclose()` 關閉上游。
    呼叫端（endpoint）必須在請求結束時呼叫 `aclose()`，不可交給垃圾回收。
    """

    def __init__(self, upstream: Any, context: StreamContext) -> None:
        self._upstream = upstream
        self._context = context
        self._is_upstream_closed = False
        self._events = self._relay()

    def __aiter__(self) -> "ChatStream":
        return self

    async def __anext__(self) -> ChatStreamItem:
        return await self._events.__anext__()

    async def aclose(self) -> None:
        """停止轉送並關閉上游；可重複呼叫。"""
        await self._events.aclose()
        await self._close_upstream()

    async def _relay(self) -> AsyncGenerator[ChatStreamItem]:
        context = self._context
        first_token_at: float | None = None
        usage: Any = None
        try:
            async for chunk in self._upstream:
                text = _chunk_text(chunk)
                if text:
                    first_token_at = first_token_at or time.perf_counter()
                    yield ChatDeltaEvent(type="delta", text=text)
                usage = getattr(chunk, "usage", None) or usage
        except context.errors as exc:
            logger.warning(
                "測試對話串流中斷：config_id=%s error=%s", context.config_id, type(exc).__name__
            )
            yield ChatErrorEvent(type="error", message=context.describe_error(exc))
            return
        finally:
            # 串流結束、出錯或被 aclose 時都立即釋放上游連線，不等到逾時
            await self._close_upstream()

        yield _done_event(context, first_token_at, usage)

    async def _close_upstream(self) -> None:
        """關閉 LiteLLM 的上游串流。

        LiteLLM 的串流物件不保證有 `aclose`，沒有就略過。關閉失敗只記 log，
        不蓋掉已產生的結果或原本的例外（finally 中拋出的例外會取代它們）。
        """
        if self._is_upstream_closed:
            return
        self._is_upstream_closed = True
        close = getattr(self._upstream, "aclose", None)
        if close is None:
            return
        try:
            result = close()
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            logger.warning(
                "關閉上游串流時發生錯誤：config_id=%s error=%s",
                self._context.config_id,
                type(exc).__name__,
            )


def _done_event(context: StreamContext, first_token_at: float | None, usage: Any) -> ChatDoneEvent:
    return ChatDoneEvent(
        type="done",
        model=context.litellm_model,
        latency_ms=_elapsed_ms(context.started, time.perf_counter()),
        first_token_ms=_elapsed_ms(context.started, first_token_at) if first_token_at else None,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        system_prompt_version=context.system_prompt_version,
    )


def _chunk_text(chunk: Any) -> str | None:
    choices = getattr(chunk, "choices", None)
    if not choices:
        return None
    content = getattr(choices[0].delta, "content", None)
    return content if isinstance(content, str) else None


def _elapsed_ms(started: float, ended: float) -> int:
    return round((ended - started) * 1000)
