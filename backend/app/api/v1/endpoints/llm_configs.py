"""LLM 模型設定 API。"""

import uuid
from collections.abc import AsyncIterable, AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.sse import EventSourceResponse

from app.api.deps import DbSession
from app.schemas.llm_chat import ChatRequest, ChatStreamEvent
from app.schemas.llm_config import LlmConfigCreate, LlmConfigRead, LlmConfigUpdate
from app.schemas.llm_provider import LlmConfigDraftCheck, LlmConfigDraftCheckRead
from app.services.llm import config_service, draft_check, gateway
from app.services.llm.chat_stream import ChatStream

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


# 用 POST：表單內容含 API 金鑰，不可放在 URL；只檢查，不儲存
@router.post(
    "/draft-checks",
    response_model=LlmConfigDraftCheckRead,
    summary="檢查設定精靈的表單內容（逐欄錯誤、建議名稱、模型查詢方式、確認摘要）",
)
async def check_llm_config_draft(
    payload: LlmConfigDraftCheck, db: DbSession
) -> LlmConfigDraftCheckRead:
    return await draft_check.check_draft(db, payload)


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
) -> AsyncIterator[ChatStream]:
    # 在 dependency 開啟串流：連線失敗能在回應開始前回傳 HTTP 錯誤，而不是 200 後才中斷。
    # 由 dependency 負責關閉：請求結束（含用戶端斷線、回應開始前被取消）時 FastAPI 一定會
    # 執行 finally；endpoint 的 generator 停在 yield 時不會被關閉，不能依賴它關閉上游
    stream = await gateway.open_chat_stream(db, config_id, payload.messages)
    try:
        yield stream
    finally:
        await stream.aclose()


@router.post(
    "/{config_id}/chat",
    response_class=EventSourceResponse,
    summary="測試對話（SSE 串流回應）",
)
async def chat_with_llm_config(
    stream: Annotated[ChatStream, Depends(_open_chat_stream)],
) -> AsyncIterable[ChatStreamEvent]:
    async for event in stream:
        yield event
