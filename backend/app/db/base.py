"""ORM 基底、約束命名規則與共用欄位 mixin。"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Dialect, MetaData, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

# 統一約束命名，SQLite 與 PostgreSQL 產生的 migration 一致
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """所有 ORM model 的基底。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UtcDateTime(TypeDecorator[datetime]):
    """一律存 UTC；SQLite 讀回的時間沒有時區，在此補上 UTC。"""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=UTC)


def utc_now() -> datetime:
    """目前的 UTC 時間。"""
    return datetime.now(UTC)


class IdMixin:
    """UUID 主鍵。"""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class CreatedAtMixin:
    """建立時間。"""

    created_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now)


class TimestampMixin(CreatedAtMixin):
    """建立與更新時間。"""

    updated_at: Mapped[datetime] = mapped_column(UtcDateTime, default=utc_now, onupdate=utc_now)
