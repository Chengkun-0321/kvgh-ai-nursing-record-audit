"""`llm_configs` 的查詢與寫入（不 commit，交易邊界在 service）。"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
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


async def get_active(session: AsyncSession) -> LlmConfig | None:
    """取得使用中的設定；尚未設定時回傳 `None`。"""
    return await session.scalar(select(LlmConfig).where(LlmConfig.is_active.is_(True)))


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


async def delete(session: AsyncSession, config: LlmConfig) -> None:
    """刪除設定。"""
    await session.delete(config)
    await session.flush()
