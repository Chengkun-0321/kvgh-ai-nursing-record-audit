"""gateway 測試共用的假串流與建立設定的 helper。"""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ChatRole, LlmProvider
from app.schemas.llm_chat import ChatMessage
from app.schemas.llm_config import LlmConfigCreate
from app.services.llm import config_service

MESSAGES = [ChatMessage(role=ChatRole.USER, content="你好")]
SYSTEM_PROMPT = "一律使用繁體中文回答。"


def chunk(text: str | None, usage: Any = None) -> SimpleNamespace:
    choices = [SimpleNamespace(delta=SimpleNamespace(content=text))] if text is not None else []
    return SimpleNamespace(choices=choices, usage=usage)


async def fake_stream(
    *chunks: SimpleNamespace, error: Exception | None = None
) -> AsyncIterator[Any]:
    for chunk in chunks:
        yield chunk
    if error is not None:
        raise error


async def create_config(session: AsyncSession, **fields: object) -> Any:
    payload = {"name": "測試", "provider": LlmProvider.OLLAMA, "model": "llama3.2", **fields}
    return await config_service.create_config(session, LlmConfigCreate.model_validate(payload))


async def collect(stream: AsyncIterator[Any]) -> list[Any]:
    return [event async for event in stream]
