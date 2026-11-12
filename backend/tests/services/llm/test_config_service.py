import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from pydantic import SecretStr
from sqlalchemy import delete, event, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session

from app.core.enums import LlmProvider, SettingChangeAction
from app.core.exceptions import ConflictError, InvalidInputError, NotFoundError
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


async def test_concurrent_rename_to_taken_name_is_reported_as_conflict(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _create(session, "本地一")
    second = await _create(session, "本地二")

    # 兩個請求同時通過名稱檢查；改名的 UPDATE 在寫入變更紀錄的 flush 時就被唯一約束擋下
    async def name_not_found(_: AsyncSession, __: str) -> None:
        return None

    monkeypatch.setattr(llm_config_crud, "get_by_name", name_not_found)

    with pytest.raises(ConflictError, match="同名"):
        await config_service.update_config(session, second.id, LlmConfigUpdate(name="本地一"))
    names = sorted(config.name for config in await config_service.list_configs(session))
    assert names == ["本地一", "本地二"]


def _delete_row_when_loaded(monkeypatch: pytest.MonkeyPatch) -> None:
    """讓 service 讀到設定後，該列立即被「另一個交易」刪除（session 內的物件不知情）。"""
    real_get = llm_config_crud.get

    async def get_then_deleted(db: AsyncSession, config_id: uuid.UUID) -> LlmConfig | None:
        config = await real_get(db, config_id)
        if config is not None:
            await db.execute(
                delete(LlmConfig.__table__).where(LlmConfig.__table__.c.id == config_id)
            )
        return config

    monkeypatch.setattr(llm_config_crud, "get", get_then_deleted)


async def test_activate_config_deleted_meanwhile_is_not_found(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _create(session, "本地一")
    second = await _create(session, "本地二")
    _delete_row_when_loaded(monkeypatch)

    with pytest.raises(NotFoundError):
        await config_service.activate_config(session, second.id)


async def test_update_config_deleted_meanwhile_is_not_found(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = await _create(session, "本地一")
    _delete_row_when_loaded(monkeypatch)

    with pytest.raises(NotFoundError):
        await config_service.update_config(session, created.id, LlmConfigUpdate(model="qwen3"))


@contextmanager
def _activate_before_delete(session: AsyncSession, config_id: uuid.UUID) -> Iterator[None]:
    """在送出 DELETE 的前一刻，模擬另一個交易把設定設為使用中。

    以核心 SQL 執行，session 內的 ORM 物件不知情。舊寫法以 flush 送出 DELETE、
    新寫法以 session.execute 送出，兩個時間點都掛上同一個動作。
    """
    table = LlmConfig.__table__
    state = {"is_done": False}

    def activate(sync_session: Session) -> None:
        if state["is_done"]:
            return
        state["is_done"] = True
        connection = sync_session.connection()
        connection.execute(update(table).where(table.c.id != config_id).values(is_active=False))
        connection.execute(update(table).where(table.c.id == config_id).values(is_active=True))

    def on_flush(sync_session: Session, *_: object) -> None:
        if any(isinstance(obj, LlmConfig) for obj in sync_session.deleted):
            activate(sync_session)

    def on_execute(orm_state: ORMExecuteState) -> None:
        if orm_state.is_delete:
            activate(orm_state.session)

    sync_session = session.sync_session
    event.listen(sync_session, "before_flush", on_flush)
    event.listen(sync_session, "do_orm_execute", on_execute)
    try:
        yield
    finally:
        event.remove(sync_session, "before_flush", on_flush)
        event.remove(sync_session, "do_orm_execute", on_execute)


async def test_config_activated_before_delete_is_kept(session: AsyncSession) -> None:
    await _create(session, "本地一")
    target = await _create(session, "本地二")
    # 刪除請求開始時目標仍非使用中，與先讀再判斷的寫法讀到的狀態相同
    assert await session.get(LlmConfig, target.id) is not None

    with (
        _activate_before_delete(session, target.id),
        pytest.raises(ConflictError, match="使用中"),
    ):
        await config_service.delete_config(session, target.id)

    # 模擬的啟用與刪除在同一個交易，衝突後一起 rollback；重點是目標設定沒有被刪掉
    remaining = [config.id for config in await config_service.list_configs(session)]
    assert target.id in remaining


async def test_delete_missing_config_is_not_found(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await config_service.delete_config(session, uuid.uuid4())
