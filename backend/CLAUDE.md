# 後端規範（FastAPI）

> 通用規範見根目錄 [CLAUDE.md](../CLAUDE.md) 與 [docs/conventions/](../docs/conventions/)。本檔只列後端專屬事項。

## 環境：套件只裝在 `backend/.venv`

首次建立（於 `backend/`）：

```bash
python3 -m venv .venv && printf '[global]\ncache-dir = %s/.pip-cache\n' "$PWD" > .venv/pip.conf
```

```bash
source .venv/bin/activate && pip install -r requirements-dev.txt
```

- `.venv/pip.conf` 讓 pip 快取也留在專案內（`backend/.pip-cache/`）
- `pip`、`python`、`ruff`、`mypy`、`alembic`、`pytest` 一律在 `.venv` 啟用狀態下執行
- 新增套件：寫入 `requirements.txt`（正式）或 `requirements-dev.txt`（開發，首行 `-r requirements.txt`），**以 `==` 鎖定版本**，再 `pip install -r requirements-dev.txt`
- Python：程式碼以 3.12 語法為下限（本機 venv 為 3.14）
- `pyproject.toml` 只放工具設定（ruff、mypy、pytest），不作為套件定義

## 核准依賴（其餘需先詢問）

- 正式：`fastapi`、`uvicorn[standard]`、`sqlalchemy[asyncio]`、`aiosqlite`、`asyncpg`、`alembic`、`pydantic-settings`、`litellm`、`cryptography`、`jinja2`、`httpx`
- 開發：`ruff`、`mypy`、`pytest`、`pytest-asyncio`

## 目錄（FastAPI 標準分層）

```
backend/
├── app/
│   ├── main.py          # 建立 app、middleware、exception handler、掛載 router
│   ├── api/
│   │   ├── deps.py      # 共用 Depends：get_db、get_settings…
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/   # patients.py、audit_findings.py、llm_configs.py…
│   ├── core/            # config.py、logging.py、security.py、exceptions.py、enums.py
│   ├── db/              # base.py（Base、mixin、naming convention）、session.py
│   ├── models/          # SQLAlchemy ORM
│   ├── schemas/         # Pydantic（Create / Update / Read 分開）
│   ├── crud/            # DB 存取，唯一直接操作 session 的層
│   ├── services/        # 商業邏輯：audit/、llm/、ingestion/
│   └── prompts/         # Jinja2 prompt 模板（版本化）
├── alembic/
├── alembic.ini
├── tests/
├── requirements.txt
├── requirements-dev.txt
└── pyproject.toml
```

各層職責與 import 限制見 [architecture.md](../docs/conventions/architecture.md)。

## FastAPI

- endpoint 只做：解析輸入 → 呼叫 service → 回傳；不寫商業邏輯、不直接操作 session
- 每個 endpoint 宣告 `response_model`、`summary`（繁中）與正確狀態碼
- 路徑：`/api/v1/<複數名詞>`，kebab-case，例：`/api/v1/audit-findings`
- 共用依賴集中於 `api/deps.py`
- `core/exceptions.py` 定義 `AppError` 階層，於 `main.py` 以 exception handler 統一轉 HTTP 回應

## Pydantic

- schema 依用途命名：`XxxCreate`、`XxxUpdate`、`XxxRead`
- ORM 轉 schema 用 `model_config = ConfigDict(from_attributes=True)`；不直接回傳 ORM 物件
- 列舉（如 `Verdict`）只在 `core/enums.py` 定義一次，models 與 schemas 共用

## SQLAlchemy（async、2.0 寫法）

- 使用 `Mapped[]` / `mapped_column()` / `select()`；禁用 1.x `Query` API
- `AsyncSession` 由 `get_db` 提供，`expire_on_commit=False`
- **交易邊界在 service**：`crud` 只查詢、新增、修改，不 `commit`
- 關聯資料用 `selectinload()` 預載，避免 N+1
- 共用欄位（`id: Uuid`、`created_at`、`updated_at`）放 `db/base.py` 的 mixin
- 資料表名稱：snake_case 複數（`audit_findings`）

## DB 可攜性（SQLite → PostgreSQL）

詳見 [ADR 0001](../docs/adr/0001-sqlite-to-postgresql.md)。

- UUID 用 `sqlalchemy.Uuid`；JSON 用 `sqlalchemy.JSON`（不用 `JSONB`、`ARRAY`）；Enum 用 `Enum(..., native_enum=False)` 存字串
- 時間欄位 `DateTime(timezone=True)`，一律存 UTC；業務日期（`business_date`）以 Asia/Taipei 計算
- 禁用方言專屬語法（`INSERT OR REPLACE`、`ON CONFLICT`…）；確需 upsert 時封裝在 crud，並確保兩種方言皆可運作
- raw SQL 只允許在 crud，且必須用 bound parameters
- `db/base.py` 的 `MetaData(naming_convention=...)` 統一約束命名

## Alembic

- 每次 model 變更：`alembic revision --autogenerate -m "繁中描述"` → **人工檢查產出** → `alembic upgrade head`
- `env.py` 設定 `render_as_batch=True`（SQLite 的 ALTER TABLE 限制）
- 已 commit 的 migration 不得修改，只能新增；每個 migration 都要能 `downgrade`
- migration 與對應 model 變更放同一個 commit

## 設定與 log

- 設定一律經 `core/config.py` 的 `Settings(BaseSettings)`，透過 `get_settings()`（`lru_cache`）取得；新增設定同步更新 `.env.example`
- log 用 `logging.getLogger(__name__)`，禁用 `print`；log 只記 `patient_key`、`record_id`
- async 函式內禁止阻塞 I/O（`requests`、`time.sleep`、大量同步檔案讀寫）；對外 HTTP 用 `httpx.AsyncClient`

## 檢查

```bash
ruff check . && ruff format --check . && mypy app
```
