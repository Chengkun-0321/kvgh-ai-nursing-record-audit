import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.crud import llm_system_prompt as llm_system_prompt_crud
from app.models.llm_system_prompt import LlmSystemPrompt
from app.models.setting_change_log import SettingChangeLog
from app.schemas.llm_system_prompt import LlmSystemPromptCreate
from app.services.llm import system_prompt_service


async def _save(session: AsyncSession, content: str) -> int | None:
    """以目前的最新版本為基準儲存（模擬畫面上已是最新內容）。"""
    current = await system_prompt_service.get_current(session)
    payload = LlmSystemPromptCreate(content=content, base_version=current.version)
    saved = await system_prompt_service.save(session, payload)
    return saved.version


async def _version_count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(LlmSystemPrompt)) or 0


async def test_current_is_empty_before_first_save(session: AsyncSession) -> None:
    current = await system_prompt_service.get_current(session)

    assert (current.version, current.content, current.created_at) == (None, "", None)
    assert await system_prompt_service.get_for_call(session) is None


async def test_each_change_is_saved_as_new_version(session: AsyncSession) -> None:
    first = await _save(session, "  一律使用繁體中文回答。  ")
    second = await _save(session, "只根據提供的資料回答。")

    current = await system_prompt_service.get_current(session)
    assert (first, second) == (1, 2)
    assert current.content == "只根據提供的資料回答。"
    assert await _version_count(session) == 2


async def test_unchanged_content_does_not_add_version(session: AsyncSession) -> None:
    await _save(session, "一律使用繁體中文回答。")

    version = await _save(session, "一律使用繁體中文回答。")

    assert version == 1
    assert await _version_count(session) == 1


async def test_clearing_is_a_new_version_that_keeps_its_number(session: AsyncSession) -> None:
    await _save(session, "一律使用繁體中文回答。")

    version = await _save(session, "   ")

    for_call = await system_prompt_service.get_for_call(session)
    assert version == 2
    assert for_call is not None
    assert (for_call.version, for_call.content) == (2, "")


async def test_change_log_records_field_name_only(session: AsyncSession) -> None:
    await _save(session, "機密內容不應出現在紀錄")

    log = await session.scalar(select(SettingChangeLog))

    assert log is not None
    assert (log.target_type, log.changed_fields) == ("llm_system_prompt", ["content"])


async def test_saving_from_outdated_version_is_rejected(session: AsyncSession) -> None:
    await _save(session, "v1 內容")
    await _save(session, "v2 內容")

    # 舊頁面仍停在 v1
    stale = LlmSystemPromptCreate(content="舊頁面的內容", base_version=1)

    with pytest.raises(ConflictError, match="已在其他地方更新為 v2"):
        await system_prompt_service.save(session, stale)
    current = await system_prompt_service.get_current(session)
    assert (current.version, current.content) == (2, "v2 內容")


async def test_first_save_from_page_opened_after_another_save_is_rejected(
    session: AsyncSession,
) -> None:
    await _save(session, "另一個頁面先存的內容")

    with pytest.raises(ConflictError, match="為 v1"):
        await system_prompt_service.save(
            session, LlmSystemPromptCreate(content="還沒看過任何版本", base_version=None)
        )


async def test_outdated_page_with_same_content_is_not_a_conflict(session: AsyncSession) -> None:
    await _save(session, "v1 內容")
    await _save(session, "相同內容")

    saved = await system_prompt_service.save(
        session, LlmSystemPromptCreate(content="相同內容", base_version=1)
    )

    assert saved.version == 2


async def test_concurrent_save_from_same_base_version_is_a_conflict(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _save(session, "另一個請求剛存好的內容")

    # 模擬兩個請求都在對方存檔前讀到「尚無版本」：新增 v1 的 flush 被版本號唯一約束擋下
    async def no_version_yet(_: AsyncSession) -> None:
        return None

    monkeypatch.setattr(llm_system_prompt_crud, "get_latest", no_version_yet)

    with pytest.raises(ConflictError, match="已在其他地方更新"):
        await system_prompt_service.save(
            session, LlmSystemPromptCreate(content="同時儲存的內容", base_version=None)
        )
    monkeypatch.undo()
    current = await system_prompt_service.get_current(session)
    assert (current.version, current.content) == (1, "另一個請求剛存好的內容")
