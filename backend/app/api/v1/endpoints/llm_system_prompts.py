"""共用 system prompt API。"""

from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.schemas.llm_system_prompt import LlmSystemPromptCreate, LlmSystemPromptRead
from app.services.llm import system_prompt_service

router = APIRouter(prefix="/llm-system-prompts", tags=["共用 System Prompt"])


@router.get(
    "/current", response_model=LlmSystemPromptRead, summary="取得目前使用的共用 system prompt"
)
async def get_current_system_prompt(db: DbSession) -> LlmSystemPromptRead:
    return await system_prompt_service.get_current(db)


@router.post(
    "",
    response_model=LlmSystemPromptRead,
    status_code=status.HTTP_201_CREATED,
    summary="儲存共用 system prompt（新增一個版本）",
)
async def save_system_prompt(payload: LlmSystemPromptCreate, db: DbSession) -> LlmSystemPromptRead:
    return await system_prompt_service.save(db, payload)
