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
