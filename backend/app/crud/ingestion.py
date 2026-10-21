"""`ingestion_batches`、`ingestion_errors` 的查詢與寫入（不 commit，交易邊界在 service）。"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion import IngestionBatch, IngestionError


async def get_batch_by_sha256(session: AsyncSession, sha256: str) -> IngestionBatch | None:
    """依資料包 sha256 取得最早的匯入批次；未匯入過時回傳 `None`。"""
    return await session.scalar(
        select(IngestionBatch)
        .where(IngestionBatch.sha256 == sha256)
        .order_by(IngestionBatch.created_at)
        .limit(1)
    )


async def add_batch(session: AsyncSession, batch: IngestionBatch) -> IngestionBatch:
    """新增匯入批次並 flush 取得 ID。"""
    session.add(batch)
    await session.flush()
    return batch


async def add_errors(session: AsyncSession, errors: Sequence[IngestionError]) -> None:
    """新增驗證錯誤。"""
    session.add_all(errors)
    await session.flush()


async def has_errors(session: AsyncSession, batch_id: uuid.UUID, file_name: str) -> bool:
    """該批次中指定檔案是否有驗證錯誤。"""
    found = await session.scalar(
        select(IngestionError.id)
        .where(IngestionError.batch_id == batch_id, IngestionError.file_name == file_name)
        .limit(1)
    )
    return found is not None
