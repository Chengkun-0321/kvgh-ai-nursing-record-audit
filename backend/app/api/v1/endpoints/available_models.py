"""查詢可用模型 API（設定頁的模型下拉選單）。"""

from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.available_model import (
    AvailableModelsQuery,
    AvailableModelsRead,
    LocalModelsQuery,
    LocalModelsRead,
)
from app.services.llm import model_listing

router = APIRouter(prefix="/available-models", tags=["LLM 模型設定"])


# 用 POST：查詢條件含 API 金鑰，不可放在 URL
@router.post("", response_model=AvailableModelsRead, summary="查詢服務目前可用的模型")
async def query_available_models(
    payload: AvailableModelsQuery, db: DbSession
) -> AvailableModelsRead:
    return await model_listing.list_available_models(db, payload)


@router.post("/local", response_model=LocalModelsRead, summary="偵測本地伺服器類型並查詢可用模型")
async def query_local_models(payload: LocalModelsQuery, db: DbSession) -> LocalModelsRead:
    return await model_listing.detect_local_models(db, payload)
