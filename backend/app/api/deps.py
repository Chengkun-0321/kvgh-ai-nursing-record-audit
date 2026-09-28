"""共用 Depends。"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """每個請求一個 session；交易由 service commit，未 commit 的變更在結束時捨棄。"""
    async with get_session_factory()() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]
