"""gateway：共用 system prompt 的送出方式（含 ChatGPT 訂閱的 instructions）。"""

import json
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LlmProvider
from app.core.exceptions import LLMConnectionError
from app.schemas.llm_chat import ChatDoneEvent
from app.schemas.llm_system_prompt import LlmSystemPromptCreate
from app.services.llm import gateway, system_prompt_service
from tests.services.llm.gateway_helpers import (
    MESSAGES,
    SYSTEM_PROMPT,
    chunk,
    collect,
    create_config,
    fake_stream,
)


async def _save_system_prompt(session: AsyncSession, content: str) -> None:
    current = await system_prompt_service.get_current(session)
    await system_prompt_service.save(
        session, LlmSystemPromptCreate(content=content, base_version=current.version)
    )


async def test_shared_system_prompt_is_sent_first(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)
    await _save_system_prompt(session, SYSTEM_PROMPT)
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        return fake_stream(chunk("好"))

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert captured["messages"] == [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "你好"},
    ]
    assert isinstance(events[-1], ChatDoneEvent)
    assert events[-1].system_prompt_version == 1


async def test_cleared_system_prompt_sends_no_system_message_but_keeps_version(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)
    await _save_system_prompt(session, SYSTEM_PROMPT)
    await _save_system_prompt(session, "")
    captured: dict[str, Any] = {}

    async def fake_acompletion(**kwargs: Any) -> AsyncIterator[Any]:
        captured.update(kwargs)
        return fake_stream()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

    assert [message["role"] for message in captured["messages"]] == ["user"]
    assert isinstance(events[-1], ChatDoneEvent)
    assert events[-1].system_prompt_version == 2


async def test_never_saved_system_prompt_has_no_version(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await create_config(session)

    async def fake_acompletion(**_: Any) -> AsyncIterator[Any]:
        return fake_stream()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    events = await collect(await gateway.open_chat_stream(session, config.id, MESSAGES))

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
    config = await create_config(session, provider=LlmProvider.CHATGPT, model="gpt-6-luna")
    captured: list[dict[str, Any]] = []

    async def fake_post(_: AsyncHTTPHandler, **kwargs: Any) -> None:
        captured.append(kwargs["json"])
        raise httpx.ConnectError("測試中不連線")

    monkeypatch.setattr(AsyncHTTPHandler, "post", fake_post)
    with pytest.raises(LLMConnectionError):
        await gateway.open_chat_stream(session, config.id, MESSAGES)
    return captured[0]


async def test_chatgpt_sends_only_shared_system_prompt(
    session: AsyncSession, chatgpt_token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _save_system_prompt(session, SYSTEM_PROMPT)

    request = await _capture_chatgpt_request(session, chatgpt_token_dir, monkeypatch)

    assert request["instructions"] == SYSTEM_PROMPT


async def test_chatgpt_with_cleared_prompt_uses_codex_instructions(
    session: AsyncSession, chatgpt_token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _save_system_prompt(session, SYSTEM_PROMPT)
    await _save_system_prompt(session, "")

    request = await _capture_chatgpt_request(session, chatgpt_token_dir, monkeypatch)

    assert request["instructions"].startswith("You are Codex")
