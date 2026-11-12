"""設定精靈的表單檢查：逐欄錯誤、是否沿用已儲存金鑰、建議名稱、如何查詢模型、確認摘要。

規則與儲存時的檢查共用同一來源（`providers.py` 的欄位規則、`schemas/llm_config.py` 的位址檢查、
`core/constants.py` 的上限），前端不另寫一份。
"""

import re
import uuid
from dataclasses import dataclass
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.constants import (
    LLM_API_BASE_MAX_LENGTH,
    LLM_API_KEY_MAX_LENGTH,
    LLM_CONFIG_NAME_MAX_LENGTH,
    LLM_MODEL_MAX_LENGTH,
    LLM_TIMEOUT_MAX_SECONDS,
    LLM_TIMEOUT_MIN_SECONDS,
)
from app.core.enums import (
    ChatgptAuthState,
    DraftField,
    FieldRequirement,
    LlmProvider,
    ModelListPlanKind,
    WizardStepId,
)
from app.crud import llm_config as llm_config_crud
from app.models.llm_config import LlmConfig
from app.schemas.llm_config import normalize_api_base
from app.schemas.llm_provider import (
    FieldErrorRead,
    LlmConfigDraftCheck,
    LlmConfigDraftCheckRead,
    ModelListPlanRead,
    SummaryRowRead,
)
from app.services.llm import chatgpt_auth
from app.services.llm.config_summary import (
    SummaryValues,
    describe_draft_api_key,
    describe_timeout,
    summary_rows,
)
from app.services.llm.provider_catalog import LOCAL_PROVIDERS, provider_label
from app.services.llm.providers import get_provider_spec

# 依精靈的順序：連線設定 → 模型 → 命名
_FIELD_ORDER: Final = (
    DraftField.API_BASE,
    DraftField.API_KEY,
    DraftField.MODEL,
    DraftField.NAME,
    DraftField.TIMEOUT_SECONDS,
)
_STEP_FIELDS: Final[dict[WizardStepId, frozenset[DraftField]]] = {
    WizardStepId.PROVIDER: frozenset(),
    WizardStepId.CONNECTION: frozenset({DraftField.API_BASE, DraftField.API_KEY}),
    WizardStepId.MODEL: frozenset({DraftField.MODEL}),
    WizardStepId.DETAILS: frozenset({DraftField.NAME, DraftField.TIMEOUT_SECONDS}),
}
# 只接受半形數字：str.isdigit() 會接受「²」「１２０」，前者無法轉成 int，後者前端無法送出
_ASCII_DIGITS: Final = re.compile(r"[0-9]+")
_CHATGPT_SIGN_IN_REASON: Final = "請先回上一步登入 ChatGPT 帳號，登入後會列出此帳號可用的模型。"
_LOCAL_URL_REASON: Final = "伺服器位址格式正確後，會自動列出可用模型。"
_MISSING_KEY_REASON: Final = "請先回上一步填寫 API 金鑰。"


@dataclass(frozen=True)
class _DraftContext:
    draft: LlmConfigDraftCheck
    stored: LlmConfig | None
    keeps_stored_api_key: bool


async def check_draft(session: AsyncSession, draft: LlmConfigDraftCheck) -> LlmConfigDraftCheckRead:
    """檢查設定精靈的表單內容。"""
    stored = await llm_config_crud.get(session, draft.config_id) if draft.config_id else None
    context = _DraftContext(
        draft=draft, stored=stored, keeps_stored_api_key=_keeps_key(draft, stored)
    )
    errors = _errors_for_step(context)
    return LlmConfigDraftCheckRead(
        is_valid=not errors,
        errors=errors,
        keeps_stored_api_key=context.keeps_stored_api_key,
        stored_api_key_hint=_stored_key_hint(draft, stored),
        suggested_name=_suggest_name(draft),
        model_list=await _plan_model_list(context),
        summary_rows=_draft_summary(context),
    )


def _stored_key_hint(draft: LlmConfigDraftCheck, stored: LlmConfig | None) -> str | None:
    # 換了服務類型時，舊金鑰屬於另一個服務，不沿用（與儲存時的規則相同）
    if stored is None or stored.provider != draft.provider:
        return None
    return stored.api_key_hint


def _keeps_key(draft: LlmConfigDraftCheck, stored: LlmConfig | None) -> bool:
    return _stored_key_hint(draft, stored) is not None and not draft.clear_api_key


def _errors_for_step(context: _DraftContext) -> list[FieldErrorRead]:
    step_fields = _STEP_FIELDS[context.draft.step_id] if context.draft.step_id else None
    messages = {
        DraftField.API_BASE: _api_base_error(context.draft),
        DraftField.API_KEY: _api_key_error(context),
        DraftField.MODEL: _model_error(context.draft.model),
        DraftField.NAME: _name_error(context.draft.name),
        DraftField.TIMEOUT_SECONDS: _timeout_error(context.draft.timeout_seconds),
    }
    return [
        FieldErrorRead(field=field, message=message)
        for field in _FIELD_ORDER
        if (message := messages[field]) and (step_fields is None or field in step_fields)
    ]


def _api_base_error(draft: LlmConfigDraftCheck) -> str | None:
    requirement = get_provider_spec(draft.provider).api_base
    value = draft.api_base.strip()
    if requirement == FieldRequirement.UNUSED:
        return None
    if not value:
        return "請輸入 API 位址" if requirement == FieldRequirement.REQUIRED else None
    return _too_long("API 位址", value, LLM_API_BASE_MAX_LENGTH) or _url_error(value)


def _url_error(value: str) -> str | None:
    try:
        normalize_api_base(value)
    except ValueError as error:
        return str(error)
    return None


def _api_key_error(context: _DraftContext) -> str | None:
    requirement = get_provider_spec(context.draft.provider).api_key
    api_key = context.draft.api_key.strip()
    if requirement == FieldRequirement.UNUSED:
        return None
    if not api_key and not context.keeps_stored_api_key:
        return "請輸入 API 金鑰" if requirement == FieldRequirement.REQUIRED else None
    return _too_long("API 金鑰", api_key, LLM_API_KEY_MAX_LENGTH)


def _name_error(name: str) -> str | None:
    stripped = name.strip()
    if not stripped:
        return "請輸入名稱"
    return _too_long("名稱", stripped, LLM_CONFIG_NAME_MAX_LENGTH)


def _model_error(model: str) -> str | None:
    stripped = model.strip()
    if not stripped:
        return "請輸入模型名稱"
    return _too_long("模型名稱", stripped, LLM_MODEL_MAX_LENGTH)


def _too_long(label: str, value: str, max_length: int) -> str | None:
    # 上限與儲存時的 schema 共用同一組常數，檢查通過的表單儲存時不會因長度被拒
    return f"{label}最多 {max_length} 字" if len(value) > max_length else None


def _timeout_error(timeout_text: str) -> str | None:
    stripped = timeout_text.strip()
    if not stripped:
        return None
    is_valid = _ASCII_DIGITS.fullmatch(stripped) is not None and (
        LLM_TIMEOUT_MIN_SECONDS <= int(stripped) <= LLM_TIMEOUT_MAX_SECONDS
    )
    return (
        None if is_valid else f"請輸入 {LLM_TIMEOUT_MIN_SECONDS}–{LLM_TIMEOUT_MAX_SECONDS} 的整數"
    )


def _suggest_name(draft: LlmConfigDraftCheck) -> str:
    # 預設以「服務類型・模型」命名，例如「Codex・API 金鑰・gpt-5.3-codex」
    name = f"{provider_label(draft.provider)}・{draft.model.strip()}"
    return name[:LLM_CONFIG_NAME_MAX_LENGTH]


async def _plan_model_list(context: _DraftContext) -> ModelListPlanRead:
    draft = context.draft
    if draft.provider == LlmProvider.CHATGPT and not await _is_chatgpt_signed_in():
        return _blocked(_CHATGPT_SIGN_IN_REASON)
    config_id = _stored_key_config_id(context)
    if draft.provider in LOCAL_PROVIDERS:
        return _plan_local(draft, config_id)
    return _plan_remote(draft, config_id)


def _plan_local(draft: LlmConfigDraftCheck, config_id: uuid.UUID | None) -> ModelListPlanRead:
    api_base = draft.api_base.strip()
    if api_base and _url_error(api_base):
        return _blocked(_LOCAL_URL_REASON)
    return ModelListPlanRead(kind=ModelListPlanKind.LOCAL, reason=None, config_id=config_id)


def _plan_remote(draft: LlmConfigDraftCheck, config_id: uuid.UUID | None) -> ModelListPlanRead:
    needs_key = get_provider_spec(draft.provider).api_key == FieldRequirement.REQUIRED
    if needs_key and not draft.api_key.strip() and config_id is None:
        return _blocked(_MISSING_KEY_REASON)
    return ModelListPlanRead(kind=ModelListPlanKind.REMOTE, reason=None, config_id=config_id)


def _stored_key_config_id(context: _DraftContext) -> uuid.UUID | None:
    # 查模型清單時可沿用已儲存的金鑰；本地模型的兩種伺服器之間可互相沿用
    stored = context.stored
    if stored is None or stored.api_key_hint is None or context.draft.clear_api_key:
        return None
    provider = context.draft.provider
    is_same_local = provider in LOCAL_PROVIDERS and stored.provider in LOCAL_PROVIDERS
    return stored.id if is_same_local or stored.provider == provider else None


async def _is_chatgpt_signed_in() -> bool:
    status = await chatgpt_auth.get_status()
    return status.state == ChatgptAuthState.SIGNED_IN


def _blocked(reason: str) -> ModelListPlanRead:
    return ModelListPlanRead(kind=ModelListPlanKind.BLOCKED, reason=reason, config_id=None)


def _draft_summary(context: _DraftContext) -> list[SummaryRowRead]:
    draft = context.draft
    stored_hint = (
        context.stored.api_key_hint if context.stored and context.keeps_stored_api_key else None
    )
    return summary_rows(
        SummaryValues(
            provider=draft.provider,
            api_base=draft.api_base.strip() or None,
            api_key=describe_draft_api_key(
                draft.provider, typed_api_key=draft.api_key, stored_key_hint=stored_hint
            ),
            model=draft.model.strip(),
            timeout=describe_timeout(
                draft.timeout_seconds, get_settings().LLM_DEFAULT_TIMEOUT_SECONDS
            ),
        )
    )
