"""LLM 模型設定 API。"""

import uuid
from collections.abc import AsyncIterable, AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.sse import EventSourceResponse

from app.api.deps import DbSession
from app.schemas.llm_chat import ChatRequest, ChatStreamEvent
from app.schemas.llm_config import LlmConfigCreate, LlmConfigRead, LlmConfigUpdate
from app.services.llm import config_service, gateway

router = APIRouter(prefix="/llm-configs", tags=["LLM 模型設定"])


@router.get("", response_model=list[LlmConfigRead], summary="列出所有模型設定")
async def list_llm_configs(db: DbSession) -> list[LlmConfigRead]:
    return await config_service.list_configs(db)


@router.post(
    "",
    response_model=LlmConfigRead,
    status_code=status.HTTP_201_CREATED,
    summary="新增模型設定",
)
async def create_llm_config(payload: LlmConfigCreate, db: DbSession) -> LlmConfigRead:
    return await config_service.create_config(db, payload)


@router.patch("/{config_id}", response_model=LlmConfigRead, summary="更新模型設定")
async def update_llm_config(
    config_id: uuid.UUID, payload: LlmConfigUpdate, db: DbSession
) -> LlmConfigRead:
    return await config_service.update_config(db, config_id, payload)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT, summary="刪除模型設定")
async def delete_llm_config(config_id: uuid.UUID, db: DbSession) -> None:
    await config_service.delete_config(db, config_id)


@router.post("/{config_id}/activate", response_model=LlmConfigRead, summary="設為使用中的模型")
async def activate_llm_config(config_id: uuid.UUID, db: DbSession) -> LlmConfigRead:
    return await config_service.activate_config(db, config_id)


async def _open_chat_stream(
    config_id: uuid.UUID, payload: ChatRequest, db: DbSession
) -> AsyncIterator[ChatStreamEvent]:
    # 在 dependency 開啟串流：連線失敗能在回應開始前回傳 HTTP 錯誤，而不是 200 後才中斷
    return await gateway.open_chat_stream(db, config_id, payload.messages)


@router.post(
    "/{config_id}/chat",
    response_class=EventSourceResponse,
    summary="測試對話（SSE 串流回應）",
)
async def chat_with_llm_config(
    stream: Annotated[AsyncIterator[ChatStreamEvent], Depends(_open_chat_stream)],
) -> AsyncIterable[ChatStreamEvent]:
    async for event in stream:
        yield event
