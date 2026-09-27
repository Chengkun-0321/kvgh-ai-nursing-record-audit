# 架構規範

前後端各自採用框架社群的**標準目錄結構**，專案特有模組放在標準位置之下，不另創分層。

## 系統資料流

```
院方假資料 / 中繼站每日 JSON
        │  services/ingestion（DataSource）
        ▼
DB：原始批次紀錄 + 正規化病患資料
        │  services/audit（每日批次執行 AuditRule）
        │        └─→ services/llm/gateway → LiteLLM → 使用者設定的模型
        ▼
audit_findings（Verdict + Evidence）
        │  api/v1
        ▼
Next.js：病床總覽 → 點選病床顯示詳情 → 進入病患頁面 → 病患摘要 + 稽核結果 + Evidence
```

## 後端（FastAPI 標準分層）

目錄見 [backend/CLAUDE.md](../../backend/CLAUDE.md)。

### 各層職責與 import 限制

| 層          | 職責                          | 可 import                                            | 不可 import                  |
| ----------- | ----------------------------- | ---------------------------------------------------- | ---------------------------- |
| `api/`      | HTTP 輸入輸出、驗證、狀態碼   | `schemas`、`services`、`api/deps`、`core`            | `crud`、`models`、`db`       |
| `services/` | 商業邏輯、交易邊界、流程編排  | `crud`、`schemas`、`models`、`core`、其他 `services` | `api`、`fastapi`             |
| `crud/`     | DB 查詢與寫入（不 commit）    | `models`、`db`、`core`                               | `services`、`api`、`schemas` |
| `models/`   | ORM 定義                      | `db/base`、`core/enums`                              | 其他                         |
| `schemas/`  | Pydantic 資料結構             | `core/enums`                                         | `models`、`crud`、`services` |
| `core/`     | 設定、例外、列舉、log、加解密 | 標準庫與第三方                                       | `app` 內其他模組             |

依賴方向：`api → services → crud → models`，不可反向。

### `services/` 內部結構

```
services/
├── audit/
│   ├── runner.py          # run_daily_audit(business_date)：組 context → 執行規則 → 存結果
│   ├── context.py         # AuditContext 組裝（規則所需資料一次備妥）
│   ├── base.py            # AuditRule Protocol、共用 helper
│   └── rules/
│       ├── __init__.py    # RULE_REGISTRY
│       ├── r01_admission_course.py
│       └── …
├── llm/
│   ├── gateway.py         # 唯一 LLM 出口
│   ├── config_service.py  # 使用者模型設定的讀寫與加解密
│   └── prompt_loader.py   # 載入、渲染 Jinja2 prompt
└── ingestion/
    ├── sources.py         # DataSource Protocol、LocalFixtureSource、RelaySource
    ├── importer.py        # 驗證 → 正規化 → 入庫
    └── normalizers.py
```

- `run_daily_audit(business_date)` 是批次入口，可由 API、CLI 或排程呼叫（排程機制待決）
- 規則細節見 [audit-rules.md](audit-rules.md)；LLM 見 [llm.md](llm.md)；匯入見 [data-ingestion.md](data-ingestion.md)

### 預期核心資料表

| 表                    | 用途                                                 |
| --------------------- | ---------------------------------------------------- |
| `ingestion_batches`   | 每次匯入的來源、日期、檔案 checksum、狀態            |
| `ingestion_errors`    | 單筆驗證失敗紀錄                                     |
| 病患／紀錄相關表      | **待院方 JSON 格式確定後設計**                       |
| `audit_runs`          | 每次稽核批次（日期、規則集、模型、耗時、token 用量） |
| `audit_findings`      | 每位病患每條規則的 Verdict 與 Evidence               |
| `llm_configs`         | 使用者設定的模型（API key 加密存放）                 |
| `setting_change_logs` | 設定變更操作紀錄                                     |

## 前端（Next.js App Router 標準結構）

目錄見 [frontend/CLAUDE.md](../../frontend/CLAUDE.md)。

### 頁面（初步）

| 路由                     | 內容                                                                                                                                                               |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/`                      | 病房地圖：Blender 場景模組依床數組成的 3D 場景搭配病床素材，可拖曳及縮放 50–200%；依最嚴重 Verdict 顯示光暈並篩選（淡化其餘床位）；點選病床於右側（手機為 bottom sheet）顯示病患摘要與稽核結果 |
| `/patients/[patientKey]` | 病患頁面：病患摘要、各規則稽核結果、Evidence 原文（內容待討論，目前為佔位頁）                                                                                      |
| `/settings/llm`          | LLM 模型設定（provider、model、API key、測試連線）                                                                                                                 |

登入後的頁面放在 `app/(workspace)/`，共用工作區外框（頂列、側欄／底部分頁列）；登入頁（待決）之後放在此群組之外。UI 規範見 [ui-design.md](ui-design.md)。

### 資料流

- Server Component 經 `lib/api/` 取資料 → 以 props 傳給 client component 處理互動與動畫
- 前後端契約以 FastAPI OpenAPI 為準；後端 schema 變更 → 前端 `npm run gen:api`
