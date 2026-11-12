"""服務類型目錄 API：設定頁的服務類型選項、欄位規則、精靈步驟與上限。"""

from fastapi import APIRouter

from app.schemas.llm_provider import LlmProviderCatalogRead
from app.services.llm import provider_catalog

router = APIRouter(prefix="/llm-providers", tags=["LLM 模型設定"])


@router.get("", response_model=LlmProviderCatalogRead, summary="取得服務類型目錄與設定上限")
async def get_llm_provider_catalog() -> LlmProviderCatalogRead:
    return provider_catalog.get_catalog()
