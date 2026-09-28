"""Async engine 與 session factory（延遲建立，import 時不需要設定值）。"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """取得共用的 async engine。"""
    return create_async_engine(get_settings().DATABASE_URL)


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """取得 session factory；`expire_on_commit=False` 讓 commit 後仍可讀取欄位。"""
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def dispose_engine() -> None:
    """關閉連線池（應用程式結束時呼叫）。"""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
