"""v1 API router。"""

from fastapi import APIRouter, Depends

from app.api.deps import require_session
from app.api.v1.endpoints import (
    auth,
    available_models,
    chatgpt_auth,
    llm_configs,
    llm_providers,
    llm_system_prompts,
    patient_audits,
    raw_patients,
    wards,
)

# 除登入相關路由外，所有 API 都要先登入；在 router 層級套用，新增 endpoint 不必逐一宣告
protected_router = APIRouter(dependencies=[Depends(require_session)])
protected_router.include_router(llm_configs.router)
protected_router.include_router(llm_providers.router)
protected_router.include_router(chatgpt_auth.router)
protected_router.include_router(available_models.router)
protected_router.include_router(llm_system_prompts.router)
protected_router.include_router(wards.router)
protected_router.include_router(raw_patients.router)
protected_router.include_router(patient_audits.router)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(protected_router)
