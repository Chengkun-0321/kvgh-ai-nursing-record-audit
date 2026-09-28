import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import litellm
import pytest
from litellm import exceptions as litellm_errors
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChatRole, LlmProvider
from app.core.exceptions import ChatgptAuthRequiredError, LLMConnectionError
from app.schemas.llm_chat import ChatDeltaEvent, ChatDoneEvent, ChatErrorEvent, ChatMessage
from app.schemas.llm_config import LlmConfigCreate
from app.schemas.llm_system_prompt import LlmSystemPromptCreate
from app.services.llm import config_service, gateway, system_prompt_service

_MESSAGES = [ChatMessage(role=ChatRole.USER, content="你好")]
_SYSTEM_PROMPT = "一律使用繁體中文回答。"


def _chunk(text: str | None, usage: Any = None) -> SimpleNamespace:
    choices = [SimpleNamespace(delta=SimpleNamespace(content=text))] if text is not None else []
    return SimpleNamespace(choices=choices, usage=usage)


async def _fake_stream(
    *chunks: SimpleNamespace, error: Exception | None = None
) -> AsyncIterator[Any]:
    for chunk in chunks:
        yield chunk
    if error is not None:
        raise error


async def _create_config(session: AsyncSession, **fields: object) -> Any:
    payload = {"name": "測試", "provider": LlmProvider.OLLAMA, "model": "llama3.2", **fields}
    return await config_service.create_config(session, LlmConfigCreate.model_validate(payload))


async def _collect(stream: AsyncIterator[Any]) -> list[Any]:
    return [event async for event in stream]


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
    config = await _create_config(session)
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        usage = SimpleNamespace(prompt_tokens=5, completion_tokens=2)
        return _fake_stream(_chunk("你"), _chunk("好"), _chunk(None, usage=usage))

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await _collect(await gateway.open_chat_stream(session, config.id, _MESSAGES))

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
    config = await _create_config(
        session, provider=LlmProvider.OPENAI_COMPATIBLE, api_base="http://localhost:1234/v1"
    )
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        return _fake_stream()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    await _collect(await gateway.open_chat_stream(session, config.id, _MESSAGES))

    assert captured["api_key"] == "not-required"
    assert captured["model"] == "openai/llama3.2"


async def test_open_failure_raises_readable_error_without_key(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret = "sk-test-abcdefgh1234"
    config = await _create_config(
        session, provider=LlmProvider.OPENAI, model="gpt-5.3-codex", api_key=secret
    )

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.AuthenticationError(
            message=f"Incorrect API key provided: {secret}", llm_provider="openai", model="x"
        )

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError, match="API 金鑰無效") as error:
        await gateway.open_chat_stream(session, config.id, _MESSAGES)
    assert secret not in error.value.message


async def test_connection_error_names_the_server(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(session)

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.APIConnectionError(message="refused", llm_provider="ollama", model="x")

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError, match="無法連線到 http://localhost:11434"):
        await gateway.open_chat_stream(session, config.id, _MESSAGES)


async def test_bad_request_detail_is_redacted(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(session)

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.BadRequestError(
            message="OllamaException - bad key sk-leakedsecret99", model="x", llm_provider="ollama"
        )

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError) as error:
        await gateway.open_chat_stream(session, config.id, _MESSAGES)
    assert "服務拒絕此請求" in error.value.message
    assert "sk-leakedsecret99" not in error.value.message


async def test_mid_stream_error_becomes_error_event(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(session)
    timeout = litellm_errors.Timeout(message="slow", model="x", llm_provider="ollama")

    async def fake_acompletion(**_: Any) -> AsyncIterator[Any]:
        return _fake_stream(_chunk("你"), error=timeout)

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await _collect(await gateway.open_chat_stream(session, config.id, _MESSAGES))

    assert isinstance(events[-1], ChatErrorEvent)
    assert "秒沒有回應" in events[-1].message


async def test_chatgpt_without_login_is_rejected_before_calling_litellm(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(session, provider=LlmProvider.CHATGPT, model="gpt-5.3-codex")

    async def fake_acompletion(**_: Any) -> None:
        pytest.fail("未登入時不應呼叫 LiteLLM")

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(ChatgptAuthRequiredError):
        await gateway.open_chat_stream(session, config.id, _MESSAGES)


async def test_wrapped_connection_error_names_the_server(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(
        session, provider=LlmProvider.OPENAI_COMPATIBLE, api_base="http://127.0.0.1:9199/v1"
    )

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.InternalServerError(
            message="Connection error.", llm_provider="openai", model="x"
        )

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    with pytest.raises(LLMConnectionError, match=r"無法連線到 http://127\.0\.0\.1:9199/v1"):
        await gateway.open_chat_stream(session, config.id, _MESSAGES)


async def _save_system_prompt(session: AsyncSession, content: str) -> None:
    current = await system_prompt_service.get_current(session)
    await system_prompt_service.save(
        session, LlmSystemPromptCreate(content=content, base_version=current.version)
    )


async def test_shared_system_prompt_is_sent_first(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(session)
    await _save_system_prompt(session, _SYSTEM_PROMPT)
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        return _fake_stream(_chunk("好"))

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await _collect(await gateway.open_chat_stream(session, config.id, _MESSAGES))

    assert captured["messages"] == [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "你好"},
    ]
    assert isinstance(events[-1], ChatDoneEvent)
    assert events[-1].system_prompt_version == 1


async def test_cleared_system_prompt_sends_no_system_message_but_keeps_version(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(session)
    await _save_system_prompt(session, _SYSTEM_PROMPT)
    await _save_system_prompt(session, "")
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        return _fake_stream()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await _collect(await gateway.open_chat_stream(session, config.id, _MESSAGES))

    assert [message["role"] for message in captured["messages"]] == ["user"]
    assert isinstance(events[-1], ChatDoneEvent)
    assert events[-1].system_prompt_version == 2


async def test_never_saved_system_prompt_has_no_version(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create_config(session)

    async def fake_acompletion(**_: Any) -> AsyncIterator[Any]:
        return _fake_stream()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await _collect(await gateway.open_chat_stream(session, config.id, _MESSAGES))

    assert isinstance(events[-1], ChatDoneEvent)
    assert events[-1].system_prompt_version is None


async def _capture_chatgpt_request(
    session: AsyncSession, token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, Any]:
    """經過 LiteLLM 完整轉換後，攔下送往 Codex 後端的請求內容（不發出網路請求）。"""
    # gateway 會改寫這個環境變數：先 setenv 讓 monkeypatch 記下原值，測試結束後還原
    monkeypatch.setenv("CHATGPT_DEFAULT_INSTRUCTIONS", "")
    monkeypatch.delenv("CHATGPT_DEFAULT_INSTRUCTIONS")
    auth = {"access_token": "a", "refresh_token": "r", "expires_at": time.time() + 3600}
    (token_dir / "auth.json").write_text(json.dumps({**auth, "account_id": "acct-test"}))
    config = await _create_config(session, provider=LlmProvider.CHATGPT, model="gpt-6-luna")
    captured: list[dict[str, Any]] = []

    async def fake_post(_: AsyncHTTPHandler, **kwargs: Any) -> None:
        captured.append(kwargs["json"])
        raise httpx.ConnectError("測試中不連線")

    monkeypatch.setattr(AsyncHTTPHandler, "post", fake_post)
    with pytest.raises(LLMConnectionError):
        await gateway.open_chat_stream(session, config.id, _MESSAGES)
    return captured[0]


async def test_chatgpt_sends_only_shared_system_prompt(
    session: AsyncSession, chatgpt_token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _save_system_prompt(session, _SYSTEM_PROMPT)

    request = await _capture_chatgpt_request(session, chatgpt_token_dir, monkeypatch)

    assert request["instructions"] == _SYSTEM_PROMPT


async def test_chatgpt_with_cleared_prompt_uses_codex_instructions(
    session: AsyncSession, chatgpt_token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _save_system_prompt(session, _SYSTEM_PROMPT)
    await _save_system_prompt(session, "")

    request = await _capture_chatgpt_request(session, chatgpt_token_dir, monkeypatch)

    assert request["instructions"].startswith("You are Codex")
