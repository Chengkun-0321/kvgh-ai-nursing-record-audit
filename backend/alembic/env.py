"""Alembic 環境：連線字串取自 Settings，SQLite 使用 batch 模式處理 ALTER TABLE。"""

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic.autogenerate.api import AutogenContext
from sqlalchemy import DateTime, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  # 註冊所有資料表到 Base.metadata
from alembic import context
from app.core.config import get_settings
from app.db.base import Base, UtcDateTime

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | bool:
    # migration 不依賴 app 內的自訂型別：UtcDateTime 以一般 DateTime(timezone=True) 產出
    if type_ == "type" and isinstance(obj, UtcDateTime):
        return repr(DateTime(timezone=True)).replace("DateTime", "sa.DateTime", 1)
    return False


def _configure_options() -> dict[str, Any]:
    return {
        "target_metadata": target_metadata,
        "render_as_batch": True,
        "render_item": _render_item,
        "compare_type": True,
    }


def run_migrations_offline() -> None:
    """產生 SQL 而不連線 DB。"""
    context.configure(
        url=get_settings().DATABASE_URL,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_configure_options(),
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, **_configure_options())
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    settings = get_settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """連線 DB 執行 migration。"""
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
