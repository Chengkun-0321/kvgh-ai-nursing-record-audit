"""共用 system prompt 的讀取與儲存（交易邊界在此）。

每次儲存新增一個版本、不修改舊版本，稽核結果記錄所用的版本號即可重現當時的 prompt。
"""

import logging
from dataclasses import dataclass
from typing import Final

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SettingChangeAction
from app.core.exceptions import ConflictError
from app.crud import llm_system_prompt as llm_system_prompt_crud
from app.crud import setting_change_log as setting_change_log_crud
from app.models.llm_system_prompt import LlmSystemPrompt
from app.models.setting_change_log import SettingChangeLog
from app.schemas.llm_system_prompt import LlmSystemPromptCreate, LlmSystemPromptRead

logger = logging.getLogger(__name__)

_TARGET_TYPE: Final = "llm_system_prompt"
_FIRST_VERSION: Final = 1


@dataclass(frozen=True)
class SystemPromptForCall:
    """呼叫模型時使用的版本；`content` 為空表示該版本不送 system prompt，但仍記錄版本號。"""

    version: int
    content: str


async def get_current(session: AsyncSession) -> LlmSystemPromptRead:
    """取得目前使用的版本；尚未儲存過時回傳空內容。"""
    latest = await llm_system_prompt_crud.get_latest(session)
    if latest is None:
        return LlmSystemPromptRead(version=None, content="", created_at=None)
    return _to_read(latest)


async def get_for_call(session: AsyncSession) -> SystemPromptForCall | None:
    """取得呼叫模型時使用的版本；從未儲存過時回傳 `None`。

    清空也是一個版本：內容為空時照樣回傳版本號，稽核結果才能分辨「當時已清空」與「從未設定」。
    """
    latest = await llm_system_prompt_crud.get_latest(session)
    if latest is None:
        return None
    return SystemPromptForCall(version=latest.version, content=latest.content)


async def save(session: AsyncSession, payload: LlmSystemPromptCreate) -> LlmSystemPromptRead:
    """儲存為新版本；內容與目前版本相同時不新增版本。

    Raises:
        ConflictError: 開始編輯後已有其他儲存完成（`base_version` 不是最新版本，或同時儲存）。
    """
    latest = await llm_system_prompt_crud.get_latest(session)
    current_content = latest.content if latest is not None else ""
    if payload.content == current_content:
        return await get_current(session)
    latest_version = latest.version if latest is not None else None
    if payload.base_version != latest_version:
        raise ConflictError(_outdated_message(latest_version))

    prompt = LlmSystemPrompt(
        version=latest.version + 1 if latest is not None else _FIRST_VERSION,
        content=payload.content,
    )
    await llm_system_prompt_crud.add(session, prompt)
    action = SettingChangeAction.UPDATE if latest is not None else SettingChangeAction.CREATE
    # 只記欄位名稱，不記 prompt 內容
    await setting_change_log_crud.add(
        session,
        SettingChangeLog(
            target_type=_TARGET_TYPE, target_id=prompt.id, action=action, changed_fields=["content"]
        ),
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        # 兩個請求以同一個 base_version 同時儲存：版本號唯一約束擋下後到者
        await session.rollback()
        raise ConflictError(_outdated_message(None)) from exc
    logger.info("已儲存共用 system prompt：version=%s", prompt.version)
    return _to_read(prompt)


def _outdated_message(latest_version: int | None) -> str:
    updated_to = f"為 v{latest_version}" if latest_version is not None else ""
    return f"System prompt 已在其他地方更新{updated_to}，請先複製你的內容，重新整理頁面後再儲存"


def _to_read(prompt: LlmSystemPrompt) -> LlmSystemPromptRead:
    return LlmSystemPromptRead(
        version=prompt.version, content=prompt.content, created_at=prompt.created_at
    )
