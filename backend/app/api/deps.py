"""共用 Depends。"""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.services import auth
from app.services.audit.clock import TodayProvider, taipei_today
from app.services.audit.service import AuditService
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


def get_today_provider() -> TodayProvider:
    """稽核用的「今天」（台北時間）；測試以 dependency_overrides 換成固定日期。"""
    return taipei_today


TodayProviderDep = Annotated[TodayProvider, Depends(get_today_provider)]


def get_audit_service(source: HospitalData, today: TodayProviderDep) -> AuditService:
    """稽核服務；院方資料來源與測試共用同一個 dependency override。"""
    return AuditService(source, today)


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


async def require_session(request: Request) -> str:
    """驗證 session cookie，回傳已登入的帳號；未登入或失效時拋 `AuthenticationError`（401）。"""
    return auth.verify_session_token(request.cookies.get(auth.SESSION_COOKIE_NAME))


CurrentUsername = Annotated[str, Depends(require_session)]
