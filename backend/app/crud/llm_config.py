"""`llm_configs` 的查詢與寫入（不 commit，交易邊界在 service）。"""

import uuid
from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_config import LlmConfig


async def list_all(session: AsyncSession) -> Sequence[LlmConfig]:
    """依建立時間列出所有設定。"""
    result = await session.scalars(select(LlmConfig).order_by(LlmConfig.created_at))
    return result.all()


async def get(session: AsyncSession, config_id: uuid.UUID) -> LlmConfig | None:
    """依 ID 取得設定。"""
    return await session.get(LlmConfig, config_id)


async def get_by_name(session: AsyncSession, name: str) -> LlmConfig | None:
    """依名稱取得設定。"""
    return await session.scalar(select(LlmConfig).where(LlmConfig.name == name))


async def has_any(session: AsyncSession) -> bool:
    """是否已有任何設定。"""
    return await session.scalar(select(LlmConfig.id).limit(1)) is not None


async def add(session: AsyncSession, config: LlmConfig) -> LlmConfig:
    """新增設定並 flush 取得預設值。"""
    session.add(config)
    await session.flush()
    return config


async def deactivate_others(session: AsyncSession, config_id: uuid.UUID) -> None:
    """把指定設定以外的使用中設定改為非使用中。

    部分唯一索引逐列檢查，必須先停用其他設定、再啟用目標，不可在同一個 UPDATE 內互換。
    """
    await session.execute(
        update(LlmConfig)
        .where(LlmConfig.is_active.is_(True), LlmConfig.id != config_id)
        .values(is_active=False)
    )


async def exists(session: AsyncSession, config_id: uuid.UUID) -> bool:
    """設定是否存在；直接查 DB，不採用 session 內可能過時的物件。"""
    stmt = select(LlmConfig.id).where(LlmConfig.id == config_id)
    return await session.scalar(stmt) is not None


async def delete_if_inactive(session: AsyncSession, config_id: uuid.UUID) -> bool:
    """在同一個 DELETE 內確認非使用中再刪除，回傳是否有刪到。

    先讀再刪會與同時進行的啟用交錯（讀到非使用中 → 對方啟用 → 刪掉使用中的設定）；
    條件放在 DELETE 的 WHERE，由 DB 對該列加鎖後判斷，SQLite 與 PostgreSQL 皆為原子操作。
    """
    stmt = delete(LlmConfig).where(LlmConfig.id == config_id, LlmConfig.is_active.is_(False))
    # DML 的結果實際為 CursorResult（才有 rowcount），但 execute 的型別只標 Result；
    # 不取任何欄位，列型別以 Any 表示
    result = cast(CursorResult[Any], await session.execute(stmt))
    return result.rowcount > 0
