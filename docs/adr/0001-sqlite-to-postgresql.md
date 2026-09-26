# ADR 0001：DB 由 SQLite 過渡到 PostgreSQL

- 狀態：採用
- 日期：2026-09-26

## 背景

開發與假資料測試階段使用 SQLite（免安裝、單檔），正式環境將改用 PostgreSQL。希望切換時不需改寫程式。

## 決策

- ORM：SQLAlchemy 2.0 async；驅動 `aiosqlite`（開發）／`asyncpg`（正式）
- 切換只改 `DATABASE_URL`：
  - 開發：`sqlite+aiosqlite:///./data/app.db`
  - 正式：`postgresql+asyncpg://…`
- 只使用兩者皆支援的型別：`Uuid`、`JSON`、`DateTime(timezone=True)`、`Enum(native_enum=False)`
- 禁用方言專屬語法與型別（`JSONB`、`ARRAY`、`INSERT OR REPLACE`、`ON CONFLICT`…）
- Alembic `render_as_batch=True`；`MetaData(naming_convention=...)` 統一約束命名
- 時間一律存 UTC

## 影響

- 好處：切換 DB 只改設定並在 PostgreSQL 上跑一次 `alembic upgrade head`
- 代價：切換前無法使用 PostgreSQL 專屬功能（JSONB 索引、全文檢索等）
- 後續：切換時需撰寫 SQLite → PostgreSQL 資料搬移腳本；若需 PostgreSQL 專屬功能，另立 ADR
