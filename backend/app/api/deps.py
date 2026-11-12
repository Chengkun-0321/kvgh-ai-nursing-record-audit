"""共用 Depends。"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services.hospital_data.source import HospitalDataSource


async def get_db() -> AsyncIterator[AsyncSession]:
    """每個請求一個 session；交易由 service commit，未 commit 的變更在結束時捨棄。"""
    async with get_session_factory()() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_hospital_data_source() -> HospitalDataSource:
    """院方資料來源；測試以 `dependency_overrides` 換成測試資料目錄。"""
    return HospitalDataSource(get_settings().HOSPITAL_DATA_DIR)


HospitalData = Annotated[HospitalDataSource, Depends(get_hospital_data_source)]
