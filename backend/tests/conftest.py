"""測試共用 fixture：記憶體 SQLite、測試用加密金鑰；測試不發出任何網路請求。"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

# 必須在 import app 之前設定，Settings 會快取第一次讀到的值
os.environ["LLM_KEY_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.models  # 註冊資料表
from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.services.llm import chatgpt_auth


@pytest.fixture(autouse=True)
def chatgpt_token_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """每個測試使用獨立的 ChatGPT token 目錄，不碰使用者本機的登入狀態。"""
    token_dir = tmp_path / "chatgpt"
    token_dir.mkdir()
    monkeypatch.setenv("CHATGPT_TOKEN_DIR", str(token_dir))
    # 進行中的登入與檔案鎖為模組層級狀態，每個測試重新建立
    monkeypatch.setattr(chatgpt_auth, "_store", chatgpt_auth._LoginStore())
    return token_dir


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    # StaticPool 讓同一個記憶體 DB 在多個 session 間共用
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as db_session:
        yield db_session


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as db_session:
            yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()
