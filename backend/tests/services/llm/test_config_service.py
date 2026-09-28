import uuid

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LlmProvider, SettingChangeAction
from app.core.exceptions import ConflictError, InvalidInputError
from app.core.security import decrypt_secret
from app.crud import llm_config as llm_config_crud
from app.models.llm_config import LlmConfig
from app.models.setting_change_log import SettingChangeLog
from app.schemas.llm_config import LlmConfigCreate, LlmConfigRead, LlmConfigUpdate
from app.services.llm import config_service

_TEST_KEY = "sk-test-abcdefgh1234"


async def _create(session: AsyncSession, name: str, **fields: object) -> LlmConfigRead:
    payload = {"provider": LlmProvider.OLLAMA, "model": "llama3.2", **fields}
    return await config_service.create_config(
        session, LlmConfigCreate.model_validate({"name": name, **payload})
    )


async def _active_ids(session: AsyncSession) -> list[uuid.UUID]:
    return list(await session.scalars(select(LlmConfig.id).where(LlmConfig.is_active.is_(True))))


async def test_first_config_becomes_active_and_later_ones_do_not(session: AsyncSession) -> None:
    first = await _create(session, "本地一")

    second = await _create(session, "本地二")

    assert first.is_active is True
    assert second.is_active is False
    configs = await config_service.list_configs(session)
    assert [config.name for config in configs] == ["本地一", "本地二"]


async def test_activate_keeps_single_active_config(session: AsyncSession) -> None:
    first = await _create(session, "本地一")
    second = await _create(session, "本地二")

    await config_service.activate_config(session, second.id)

    configs = {config.id: config for config in await config_service.list_configs(session)}
    assert configs[first.id].is_active is False
    assert configs[second.id].is_active is True


async def test_database_rejects_second_active_config(session: AsyncSession) -> None:
    await _create(session, "本地一")
    second = await _create(session, "本地二")
    stored_second = await session.get(LlmConfig, second.id)
    assert stored_second is not None

    stored_second.is_active = True

    with pytest.raises(IntegrityError):
        await session.commit()


async def test_concurrent_first_config_is_saved_inactive(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await _create(session, "本地一")

    # 模擬兩個請求同時新增第一筆：都以為資料表是空的
    async def always_empty(_: AsyncSession) -> bool:
        return False

    monkeypatch.setattr(llm_config_crud, "has_any", always_empty)
    second = await _create(session, "本地二")

    assert second.is_active is False
    assert await _active_ids(session) == [first.id]


async def test_concurrent_same_name_is_reported_as_conflict(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _create(session, "本地一")

    # 模擬兩個請求同時通過名稱檢查，由 DB 唯一約束擋下
    async def name_not_found(_: AsyncSession, __: str) -> None:
        return None

    monkeypatch.setattr(llm_config_crud, "get_by_name", name_not_found)

    with pytest.raises(ConflictError, match="同名"):
        await _create(session, "本地一")


async def test_activate_retries_after_concurrent_switch(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _create(session, "本地一")
    second = await _create(session, "本地二")
    real_deactivate = llm_config_crud.deactivate_others
    calls: list[uuid.UUID] = []

    # 第一次停用時看不到另一個請求剛設為使用中的設定（模擬並行），第二次才正常停用
    async def stale_then_real(db: AsyncSession, config_id: uuid.UUID) -> None:
        calls.append(config_id)
        if len(calls) > 1:
            await real_deactivate(db, config_id)

    monkeypatch.setattr(llm_config_crud, "deactivate_others", stale_then_real)
    activated = await config_service.activate_config(session, second.id)

    assert activated.is_active is True
    assert len(calls) == 2
    assert await _active_ids(session) == [second.id]


async def test_api_key_is_encrypted_and_only_hint_is_returned(session: AsyncSession) -> None:
    created = await _create(
        session, "Codex", provider=LlmProvider.OPENAI, model="gpt-5.3-codex", api_key=_TEST_KEY
    )

    stored = await session.get(LlmConfig, created.id)
    assert stored is not None
    assert stored.api_key_encrypted is not None
    assert _TEST_KEY not in stored.api_key_encrypted
    assert decrypt_secret(stored.api_key_encrypted) == _TEST_KEY
    assert created.api_key_hint == "sk-…1234"
    assert created.has_api_key is True
    assert _TEST_KEY not in created.model_dump_json()


async def test_update_without_api_key_keeps_existing_key(session: AsyncSession) -> None:
    created = await _create(
        session, "Codex", provider=LlmProvider.OPENAI, model="gpt-5.3-codex", api_key=_TEST_KEY
    )

    updated = await config_service.update_config(
        session, created.id, LlmConfigUpdate(model="gpt-5.3-codex-mini", api_key=None)
    )

    assert updated.model == "gpt-5.3-codex-mini"
    assert updated.api_key_hint == "sk-…1234"


async def test_update_to_provider_without_key_drops_stored_key(session: AsyncSession) -> None:
    created = await _create(
        session, "Codex", provider=LlmProvider.OPENAI, model="gpt-5.3-codex", api_key=_TEST_KEY
    )

    updated = await config_service.update_config(
        session, created.id, LlmConfigUpdate(provider=LlmProvider.CHATGPT)
    )

    assert updated.has_api_key is False


async def test_create_openai_without_key_is_rejected(session: AsyncSession) -> None:
    with pytest.raises(InvalidInputError):
        await _create(session, "Codex", provider=LlmProvider.OPENAI, model="gpt-5.3-codex")


async def test_duplicate_name_is_rejected(session: AsyncSession) -> None:
    await _create(session, "本地")

    with pytest.raises(ConflictError, match="同名"):
        await _create(session, "本地")


async def test_active_config_cannot_be_deleted(session: AsyncSession) -> None:
    active = await _create(session, "本地一")
    other = await _create(session, "本地二")

    with pytest.raises(ConflictError, match="使用中"):
        await config_service.delete_config(session, active.id)
    await config_service.delete_config(session, other.id)

    remaining = await config_service.list_configs(session)
    assert [config.id for config in remaining] == [active.id]


async def test_change_log_records_field_names_without_values(session: AsyncSession) -> None:
    created = await _create(
        session, "Codex", provider=LlmProvider.OPENAI, model="gpt-5.3-codex", api_key=_TEST_KEY
    )
    await config_service.update_config(
        session, created.id, LlmConfigUpdate(api_key=SecretStr("sk-test-new-key-5678"))
    )

    logs = (await session.scalars(select(SettingChangeLog))).all()
    assert [log.action for log in logs] == [SettingChangeAction.CREATE, SettingChangeAction.UPDATE]
    assert logs[1].changed_fields == ["api_key"]
    assert all("sk-test" not in str(log.changed_fields) for log in logs)


async def test_switching_to_another_keyed_provider_requires_new_key(session: AsyncSession) -> None:
    created = await _create(
        session, "Codex", provider=LlmProvider.OPENAI, model="gpt-5.3-codex", api_key=_TEST_KEY
    )

    with pytest.raises(InvalidInputError, match="API 金鑰"):
        await config_service.update_config(
            session, created.id, LlmConfigUpdate(provider=LlmProvider.GEMINI)
        )
    await session.rollback()
    updated = await config_service.update_config(
        session,
        created.id,
        LlmConfigUpdate(provider=LlmProvider.GEMINI, api_key=SecretStr("AIza-test-key-0000")),
    )

    assert updated.api_key_hint == "AIz…0000"
