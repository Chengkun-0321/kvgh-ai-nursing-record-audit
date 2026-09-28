"""模型設定的讀寫、使用中切換與變更紀錄（交易邊界在此）。"""

import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final

from pydantic import SecretStr
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import LlmProvider, SettingChangeAction
from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import encrypt_secret, mask_secret
from app.crud import llm_config as llm_config_crud
from app.crud import setting_change_log as setting_change_log_crud
from app.models.llm_config import LlmConfig
from app.models.setting_change_log import SettingChangeLog
from app.schemas.llm_config import LlmConfigCreate, LlmConfigRead, LlmConfigUpdate
from app.services.llm.providers import FieldRequirement, check_required_fields, get_provider_spec

logger = logging.getLogger(__name__)

_TARGET_TYPE: Final = "llm_config"
_API_KEY_FIELD: Final = "api_key"
# PATCH 可變更的一般欄位；API 金鑰另外處理
_UPDATABLE_FIELDS: Final = frozenset({"name", "provider", "model", "api_base", "timeout_seconds"})
# 這些欄位傳 null 表示清除；其餘欄位傳 null 視為未變更
_NULLABLE_FIELDS: Final = frozenset({"api_base"})
_NAME_TAKEN_MESSAGE: Final = "已有同名的設定，請改用其他名稱"
_ACTIVE_CHANGED_MESSAGE: Final = "使用中的設定剛被其他操作變更，請重新整理頁面後再試"


@dataclass(frozen=True)
class StoredLlmConfig:
    """gateway 呼叫模型所需的設定；API 金鑰仍為密文，呼叫當下才解密。"""

    id: uuid.UUID
    provider: LlmProvider
    model: str
    api_base: str | None
    api_key_encrypted: str | None
    timeout_seconds: int


async def list_configs(session: AsyncSession) -> list[LlmConfigRead]:
    """列出所有模型設定。"""
    return [
        LlmConfigRead.model_validate(config) for config in await llm_config_crud.list_all(session)
    ]


async def create_config(session: AsyncSession, payload: LlmConfigCreate) -> LlmConfigRead:
    """新增模型設定；第一筆設定自動設為使用中，其餘不影響目前使用中的設定。

    Raises:
        ConflictError: 名稱重複。
        InvalidInputError: 缺少該服務類型的必填欄位。
    """
    await _ensure_name_available(session, payload.name, exclude_id=None)
    is_first = not await llm_config_crud.has_any(session)
    try:
        return await _insert_config(session, payload, is_active=is_first)
    except IntegrityError as exc:
        await session.rollback()
        if not is_first:
            raise ConflictError(_NAME_TAKEN_MESSAGE) from exc
    # 同時新增第一筆：另一筆已先成為使用中，改為非使用中再新增一次；仍失敗即為名稱重複
    try:
        return await _insert_config(session, payload, is_active=False)
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(_NAME_TAKEN_MESSAGE) from exc


async def update_config(
    session: AsyncSession, config_id: uuid.UUID, payload: LlmConfigUpdate
) -> LlmConfigRead:
    """部分更新模型設定；不影響使用中狀態。

    Raises:
        NotFoundError: 查無設定。
        ConflictError: 名稱重複。
        InvalidInputError: 更新後缺少該服務類型的必填欄位。
    """
    config = await _get_or_raise(session, config_id)
    if payload.name is not None and payload.name != config.name:
        await _ensure_name_available(session, payload.name, exclude_id=config.id)

    changed_fields = _apply_field_changes(config, payload)
    if _apply_api_key_change(config, payload, is_provider_changed="provider" in changed_fields):
        changed_fields.add(_API_KEY_FIELD)
    changed_fields |= _drop_unused_fields(config)
    _check_config(config)

    if changed_fields:
        await _log_change(session, config.id, SettingChangeAction.UPDATE, changed_fields)
        await _commit(session)
        logger.info("已更新模型設定：config_id=%s fields=%s", config.id, sorted(changed_fields))
    return LlmConfigRead.model_validate(config)


async def activate_config(session: AsyncSession, config_id: uuid.UUID) -> LlmConfigRead:
    """把指定設定設為使用中，其他設定改為非使用中（同一交易）。

    Raises:
        NotFoundError: 查無設定。
        ConflictError: 重試後仍與同時進行的切換衝突。
    """
    try:
        return await _activate(session, config_id)
    except IntegrityError:
        await session.rollback()
    # 同時切換：另一個請求先完成，讀取最新狀態後再切換一次
    try:
        return await _activate(session, config_id)
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(_ACTIVE_CHANGED_MESSAGE) from exc


async def delete_config(session: AsyncSession, config_id: uuid.UUID) -> None:
    """刪除模型設定；使用中的設定不可刪除。

    Raises:
        NotFoundError: 查無設定。
        ConflictError: 該設定為使用中。
    """
    config = await _get_or_raise(session, config_id)
    if config.is_active:
        raise ConflictError("使用中的設定無法刪除，請先將其他設定設為使用中")

    await llm_config_crud.delete(session, config)
    await _log_change(session, config_id, SettingChangeAction.DELETE, set())
    await _commit(session)
    logger.info("已刪除模型設定：config_id=%s", config_id)


async def get_stored_config(session: AsyncSession, config_id: uuid.UUID) -> StoredLlmConfig:
    """取得 gateway 呼叫所需的設定。

    Raises:
        NotFoundError: 查無設定。
    """
    config = await _get_or_raise(session, config_id)
    return StoredLlmConfig(
        id=config.id,
        provider=config.provider,
        model=config.model,
        api_base=config.api_base,
        api_key_encrypted=config.api_key_encrypted,
        timeout_seconds=config.timeout_seconds,
    )


async def _insert_config(
    session: AsyncSession, payload: LlmConfigCreate, *, is_active: bool
) -> LlmConfigRead:
    config = LlmConfig(
        name=payload.name,
        provider=payload.provider,
        model=payload.model,
        api_base=payload.api_base,
        timeout_seconds=payload.timeout_seconds or get_settings().LLM_DEFAULT_TIMEOUT_SECONDS,
        is_active=is_active,
    )
    _store_api_key(config, _plain_api_key(payload.api_key))
    _drop_unused_fields(config)
    _check_config(config)

    await llm_config_crud.add(session, config)
    await _log_change(session, config.id, SettingChangeAction.CREATE, payload.model_fields_set)
    await session.commit()
    logger.info("已新增模型設定：config_id=%s", config.id)
    return LlmConfigRead.model_validate(config)


async def _activate(session: AsyncSession, config_id: uuid.UUID) -> LlmConfigRead:
    config = await _get_or_raise(session, config_id)
    if config.is_active:
        return LlmConfigRead.model_validate(config)

    # 先停用其他設定再啟用目標；同時切換時後到者違反部分唯一索引，由呼叫端重試
    await llm_config_crud.deactivate_others(session, config.id)
    config.is_active = True
    await _log_change(session, config.id, SettingChangeAction.ACTIVATE, {"is_active"})
    await session.commit()
    logger.info("已切換使用中的模型設定：config_id=%s", config.id)
    return LlmConfigRead.model_validate(config)


async def _get_or_raise(session: AsyncSession, config_id: uuid.UUID) -> LlmConfig:
    config = await llm_config_crud.get(session, config_id)
    if config is None:
        raise NotFoundError("找不到這組模型設定，可能已被刪除，請重新整理頁面")
    return config


async def _ensure_name_available(
    session: AsyncSession, name: str, *, exclude_id: uuid.UUID | None
) -> None:
    existing = await llm_config_crud.get_by_name(session, name)
    if existing is not None and existing.id != exclude_id:
        raise ConflictError(_NAME_TAKEN_MESSAGE)


def _plain_api_key(api_key: SecretStr | None) -> str | None:
    if api_key is None:
        return None
    return api_key.get_secret_value().strip() or None


def _store_api_key(config: LlmConfig, plain: str | None) -> None:
    config.api_key_encrypted = encrypt_secret(plain) if plain else None
    config.api_key_hint = mask_secret(plain) if plain else None


def _apply_field_changes(config: LlmConfig, payload: LlmConfigUpdate) -> set[str]:
    changed: set[str] = set()
    for field in payload.model_fields_set & _UPDATABLE_FIELDS:
        value = getattr(payload, field)
        if value is None and field not in _NULLABLE_FIELDS:
            continue
        if getattr(config, field) != value:
            setattr(config, field, value)
            changed.add(field)
    return changed


def _apply_api_key_change(
    config: LlmConfig, payload: LlmConfigUpdate, *, is_provider_changed: bool
) -> bool:
    new_key = _plain_api_key(payload.api_key)
    if new_key is not None:
        _store_api_key(config, new_key)
        return True
    # 換了服務類型卻沒給新金鑰：舊金鑰屬於另一個服務，不可沿用
    should_clear = payload.clear_api_key or is_provider_changed
    if should_clear and config.api_key_encrypted is not None:
        _store_api_key(config, None)
        return True
    return False


def _drop_unused_fields(config: LlmConfig) -> set[str]:
    """切換服務類型後，清掉新類型用不到的欄位，避免留下無用的金鑰。"""
    spec = get_provider_spec(config.provider)
    dropped: set[str] = set()
    if spec.api_key == FieldRequirement.UNUSED and config.api_key_encrypted is not None:
        _store_api_key(config, None)
        dropped.add(_API_KEY_FIELD)
    if spec.api_base == FieldRequirement.UNUSED and config.api_base is not None:
        config.api_base = None
        dropped.add("api_base")
    return dropped


def _check_config(config: LlmConfig) -> None:
    check_required_fields(
        config.provider,
        has_api_key=config.api_key_encrypted is not None,
        api_base=config.api_base,
    )


async def _log_change(
    session: AsyncSession,
    config_id: uuid.UUID,
    action: SettingChangeAction,
    fields: Iterable[str],
) -> None:
    # 只記欄位名稱，不記任何值（尤其是 API 金鑰）
    log = SettingChangeLog(
        target_type=_TARGET_TYPE,
        target_id=config_id,
        action=action,
        changed_fields=sorted(fields),
    )
    await setting_change_log_crud.add(session, log)


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as exc:
        # 名稱唯一約束：兩個請求同時改用同一名稱時才會走到這裡
        await session.rollback()
        raise ConflictError(_NAME_TAKEN_MESSAGE) from exc
