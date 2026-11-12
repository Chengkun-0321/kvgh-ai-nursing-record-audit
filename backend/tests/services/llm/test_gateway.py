"""gateway：串流、錯誤訊息轉換與 ChatGPT 登入檢查。"""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import litellm
import pytest
from litellm import exceptions as litellm_errors
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LlmProvider
from app.core.exceptions import ChatgptAuthRequiredError, LLMConnectionError
from app.schemas.llm_chat import ChatDeltaEvent, ChatDoneEvent, ChatErrorEvent
from app.services.llm import gateway
from tests.services.llm.gateway_helpers import (
    MESSAGES,
    chunk,
    collect,
    create_config,
    fake_stream,
)


def test_error_tuple_covers_all_litellm_exception_types() -> None:
    uncovered = [
        error.__name__
        for error in litellm.LITELLM_EXCEPTION_TYPES
        if not issubclass(error, gateway.LITELLM_ERRORS)
    ]

    assert uncovered == []


async def test_stream_yields_deltas_then_done_with_usage(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        usage = SimpleNamespace(prompt_tokens=5, completion_tokens=2)
        return fake_stream(chunk("你"), chunk("好"), chunk(None, usage=usage))

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert [event.text for event in events if isinstance(event, ChatDeltaEvent)] == ["你", "好"]
    done = events[-1]
    assert isinstance(done, ChatDoneEvent)
    assert (done.model, done.prompt_tokens, done.completion_tokens) == (
        "ollama_chat/llama3.2",
        5,
        2,
    )
    assert captured["api_base"] == "http://localhost:11434"
    assert "temperature" not in captured


async def test_openai_compatible_without_key_sends_placeholder(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(
        session, provider=LlmProvider.OPENAI_COMPATIBLE, api_base="http://localhost:1234/v1"
    )
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        return fake_stream()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert captured["api_key"] == "not-required"
    assert captured["model"] == "openai/llama3.2"


async def test_open_failure_raises_readable_error_without_key(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "sk-test-abcdefgh1234"
    config = await create_config(
        session, provider=LlmProvider.OPENAI, model="gpt-5.3-codex", api_key=secret
    )

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.AuthenticationError(
            message=f"Incorrect API key provided: {secret}", llm_provider="openai", model="x"
        )

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError, match="API 金鑰無效") as error:
        await gateway.open_chat_stream(session, config.id, MESSAGES)
    assert secret not in error.value.message


async def test_connection_error_names_the_server(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.APIConnectionError(message="refused", llm_provider="ollama", model="x")

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError, match="無法連線到 http://localhost:11434"):
        await gateway.open_chat_stream(session, config.id, MESSAGES)


async def test_bad_request_detail_is_redacted(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.BadRequestError(
            message="OllamaException - bad key sk-leakedsecret99", model="x", llm_provider="ollama"
        )

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError) as error:
        await gateway.open_chat_stream(session, config.id, MESSAGES)
    assert "服務拒絕此請求" in error.value.message
    assert "sk-leakedsecret99" not in error.value.message


async def test_mid_stream_error_becomes_error_event(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)
    timeout = litellm_errors.Timeout(message="slow", model="x", llm_provider="ollama")

    async def fake_acompletion(**_: Any) -> AsyncIterator[Any]:
        return fake_stream(chunk("你"), error=timeout)

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert isinstance(events[-1], ChatErrorEvent)
    assert "秒沒有回應" in events[-1].message


async def test_chatgpt_without_login_is_rejected_before_calling_litellm(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session, provider=LlmProvider.CHATGPT, model="gpt-5.3-codex")

    async def fake_acompletion(**_: Any) -> None:
        pytest.fail("未登入時不應呼叫 LiteLLM")

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(ChatgptAuthRequiredError):
        await gateway.open_chat_stream(session, config.id, MESSAGES)


async def test_wrapped_connection_error_names_the_server(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(
        session, provider=LlmProvider.OPENAI_COMPATIBLE, api_base="http://127.0.0.1:9199/v1"
    )

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.InternalServerError(
            message="Connection error.", llm_provider="openai", model="x"
        )

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError, match=r"無法連線到 http://127\.0\.0\.1:9199/v1"):
        await gateway.open_chat_stream(session, config.id, MESSAGES)


async def test_db_transaction_ends_before_calling_litellm(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """讀完設定就結束交易、歸還連線；串流期間不占用連線池。"""
    config = await create_config(session)
    transaction_open_during_call: list[bool] = []

    async def fake_acompletion(**_: Any) -> AsyncIterator[Any]:
        transaction_open_during_call.append(session.in_transaction())
        return fake_stream(chunk("好"))

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert transaction_open_during_call == [False]


class _FakeUpstream:
    """模擬 LiteLLM 的串流物件：記錄是否被關閉。"""

    def __init__(self, *texts: str) -> None:
        self._chunks = [chunk(text) for text in texts]
        self.closed = False
        self.close_count = 0

    def __aiter__(self) -> "_FakeUpstream":
        return self

    async def __anext__(self) -> SimpleNamespace:
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)

    async def aclose(self) -> None:
        self.closed = True
        self.close_count += 1


class _UpstreamWithoutClose:
    """沒有 aclose 的上游，確認關閉時不會因此出錯。"""

    def __init__(self) -> None:
        self._chunks = [chunk("好")]

    def __aiter__(self) -> "_UpstreamWithoutClose":
        return self

    async def __anext__(self) -> SimpleNamespace:
        if not self._chunks:
            raise StopAsyncIteration
        return self._chunks.pop(0)


async def test_client_disconnect_closes_upstream(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)
    upstream = _FakeUpstream("你", "好", "嗎")

    async def fake_acompletion(**_: Any) -> _FakeUpstream:
        return upstream

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)
    stream = await gateway.open_chat_stream(session, config.id, MESSAGES)

    assert isinstance(await anext(stream), ChatDeltaEvent)
    await stream.aclose()

    assert upstream.closed is True


async def test_finished_stream_closes_upstream(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)
    upstream = _FakeUpstream("好")

    async def fake_acompletion(**_: Any) -> _FakeUpstream:
        return upstream

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert isinstance(events[-1], ChatDoneEvent)
    assert upstream.closed is True


async def test_upstream_without_aclose_still_completes(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)

    async def fake_acompletion(**_: Any) -> _UpstreamWithoutClose:
        return _UpstreamWithoutClose()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert isinstance(events[-1], ChatDoneEvent)


async def test_unstarted_stream_aclose_closes_upstream(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """回應開始前就取消：串流從未被迭代，aclose 仍要關閉已開啟的上游。"""
    config = await create_config(session)
    upstream = _FakeUpstream("好")

    async def fake_acompletion(**_: Any) -> _FakeUpstream:
        return upstream

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)
    stream = await gateway.open_chat_stream(session, config.id, MESSAGES)

    await stream.aclose()

    assert upstream.closed is True


async def test_upstream_is_closed_only_once(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)
    upstream = _FakeUpstream("好")

    async def fake_acompletion(**_: Any) -> _FakeUpstream:
        return upstream

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)
    stream = await gateway.open_chat_stream(session, config.id, MESSAGES)

    await collect(stream)
    await stream.aclose()
    await stream.aclose()

    assert upstream.close_count == 1
