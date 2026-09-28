"""v1 API router。"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    available_models,
    chatgpt_auth,
    llm_configs,
    llm_system_prompts,
)

api_router = APIRouter()
api_router.include_router(llm_configs.router)
api_router.include_router(chatgpt_auth.router)
api_router.include_router(available_models.router)
api_router.include_router(llm_system_prompts.router)
