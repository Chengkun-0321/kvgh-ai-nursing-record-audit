"""gateway 併發：ChatGPT 指示只能透過程序共用的環境變數傳遞，同時呼叫時必須各自拿到自己的指示。"""

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
import pytest
from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.enums import ChatRole, LlmProvider
from app.core.exceptions import LLMConnectionError
from app.schemas.llm_chat import ChatMessage
from app.services.llm import config_service, gateway, system_prompt_service
from app.services.llm.config_service import StoredLlmConfig
from app.services.llm.system_prompt_service import SystemPromptForCall

# 以 task 名稱區分兩個同時進行的呼叫，各自對應一段 system prompt
_PROMPTS = {"alpha": "指示甲：只用條列回答。", "beta": "指示乙：只用一句話回答。"}
_USER_TEXT = {"alpha": "問題甲", "beta": "問題乙"}


def _write_chatgpt_login(token_dir: Path) -> None:
    auth = {
        "access_token": "a",
        "refresh_token": "r",
        "expires_at": time.time() + 3600,
        "account_id": "acct-test",
    }
    (token_dir / "auth.json").write_text(json.dumps(auth))


def _chatgpt_config() -> StoredLlmConfig:
    return StoredLlmConfig(
        id=uuid.uuid4(),
        provider=LlmProvider.CHATGPT,
        model="gpt-6-luna",
        api_base=None,
        api_key_encrypted=None,
        timeout_seconds=30,
    )


async def test_concurrent_chatgpt_calls_each_send_their_own_instructions(
    session_factory: async_sessionmaker[AsyncSession],
    chatgpt_token_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_chatgpt_login(chatgpt_token_dir)
    # 不經 DB：讀取設定與 prompt 的部分已由其他測試覆蓋，這裡只驗證併發時的送出內容
    config = _chatgpt_config()
    monkeypatch.delenv("CHATGPT_DEFAULT_INSTRUCTIONS", raising=False)

    async def fake_get_stored_config(_: AsyncSession, __: uuid.UUID) -> StoredLlmConfig:
        return config

    async def fake_get_for_call(_: AsyncSession) -> SystemPromptForCall:
        task = asyncio.current_task()
        assert task is not None
        name = task.get_name()
        return SystemPromptForCall(version=1, content=_PROMPTS[name])

    sent: dict[str, str] = {}

    async def fake_post(_: AsyncHTTPHandler, **kwargs: Any) -> None:
        body = kwargs["json"]
        user_text = body["input"][-1]["content"][0]["text"]
        sent[user_text] = body["instructions"]
        raise httpx.ConnectError("測試中不連線")

    monkeypatch.setattr(config_service, "get_stored_config", fake_get_stored_config)
    monkeypatch.setattr(system_prompt_service, "get_for_call", fake_get_for_call)
    monkeypatch.setattr(AsyncHTTPHandler, "post", fake_post)

    async def run(name: str) -> None:
        messages = [ChatMessage(role=ChatRole.USER, content=_USER_TEXT[name])]
        async with session_factory() as db:
            with pytest.raises(LLMConnectionError):
                await gateway.open_chat_stream(db, config.id, messages)

    await asyncio.gather(
        asyncio.create_task(run("alpha"), name="alpha"),
        asyncio.create_task(run("beta"), name="beta"),
    )

    assert sent == {"問題甲": _PROMPTS["alpha"], "問題乙": _PROMPTS["beta"]}
