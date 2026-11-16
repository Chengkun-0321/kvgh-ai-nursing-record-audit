# 架構規範

前後端各自採用框架社群的**標準目錄結構**，專案特有模組放在標準位置之下，不另創分層。

## 系統資料流

```
院方每日 JSON（data/<YYYYMMDD>/<病房>/，只讀，不入庫，ADR 0010）
        │  services/hospital_data（跨日合併；稽核歸日依紀錄本身的時間，ADR 0011）
        │
        ├─→ services/audit（手動觸發 AuditRule，ADR 0011）
        │        └─→ services/llm/gateway → LiteLLM → 使用者設定的模型
        │        ▼
        │   audit_runs（每次執行一列）＋ audit_findings（Verdict + Evidence）
        │
        ▼
api/v1 → Next.js：病床總覽（W63）、原始資料頁、病患頁（稽核結果與 Evidence）

（中繼站匯入 services/ingestion 尚未實作，見 data-ingestion.md。）
```

## 前後端分工

**領域運算與驗證一律在後端，前端只負責渲染**（見 [ADR 0009](../adr/0009-backend-owns-computation.md)）。

| 由後端提供（前端不得自行計算或另存一份規則） | 前端可以做的事 |
| --- | --- |
| 病床狀態、各狀態床數、待處理床數、摘要文字、住院天數 | 狀態 → 顏色與圖示的對照、日期格式化 |
| 原始資料的跨日合併、去重、排序、篩選、依日分組、檢驗矩陣、異常標記 | 篩選造成的淡化、選取狀態、表單草稿 |
| LLM 設定的欄位規則、上限、逐欄錯誤、建議名稱、確認摘要、模型清單是否可查 | 把表單欄位組成 API 請求 |
| 服務類型與狀態的顯示名稱 | 3D 場景版面與相機（`wardLayout.ts`、`wardProjection.ts`，屬畫面呈現） |

新增需要判斷的畫面時，先在後端 API 加欄位，不在前端寫判斷。

## 後端（FastAPI 標準分層）

目錄見 [backend/CLAUDE.md](../../backend/CLAUDE.md)。

### 各層職責與 import 限制

| 層          | 職責                          | 可 import                                            | 不可 import                  |
| ----------- | ----------------------------- | ---------------------------------------------------- | ---------------------------- |
| `api/`      | HTTP 輸入輸出、驗證、狀態碼   | `schemas`、`services`、`api/deps`、`core`            | `crud`、`models`、`db`       |
| `services/` | 商業邏輯、交易邊界、流程編排  | `crud`、`schemas`、`models`、`core`、其他 `services` | `api`、`fastapi`             |
| `crud/`     | DB 查詢與寫入（不 commit）    | `models`、`db`、`core`                               | `services`、`api`、`schemas` |
| `models/`   | ORM 定義                      | `db/base`、`core/enums`、`core/constants`            | 其他                         |
| `schemas/`  | Pydantic 資料結構             | `core/enums`、`core/constants`                       | `models`、`crud`、`services` |
| `core/`     | 設定、例外、列舉、log、加解密 | 標準庫與第三方                                       | `app` 內其他模組             |

依賴方向：`api → services → crud → models`，不可反向。

唯一例外：`api/deps.py` 為了提供 `get_db`（每個請求一個 session）會 import `db.session`；這是 FastAPI 提供 session 的標準位置，其他 `api/` 檔案仍不可 import `db`。

### `services/` 內部結構

```
services/
├── audit/                 # 稽核模組（ADR 0011）
│   ├── service.py         # AuditService：固定流程、稽核週期、每日總覽；交易邊界在此
│   ├── context.py         # build_audit_context：一次備妥病患所有日期的紀錄（不入庫）
│   ├── records.py         # 院方紀錄 → SourceRecord；渲染 prompt 的 <record> 區塊
│   ├── evidence.py        # LLM 輸出的 Evidence 核對、WARNING 降級、整體判定
│   ├── severity.py        # 判定嚴重度排序（整體判定與病床狀態共用）
│   ├── text.py            # 比對用的文字正規化（去除雜訊字元）
│   ├── registry.py        # RULE_REGISTRY：新增規則時在此註冊一行
│   ├── runs.py            # 核對後的結果 → AuditRun／AuditFinding（不含 DB 操作）
│   ├── views.py           # ORM → 回應結構
│   ├── labels.py          # 狀態、週期、可否執行的繁中文字
│   └── rules/
│       ├── base.py        # AuditRule Protocol、Availability、AuditInput
│       ├── r01_admission_course.py … r07_medication_followup.py
│       └── r02_comparison.py、r04_checks.py、r04_output.py（規則的輔助模組）
├── llm/
│   ├── __init__.py        # 內網：改用 LiteLLM 內建的模型價格表
│   ├── gateway.py         # 唯一 LLM 出口：測試對話串流、complete_structured（重新匯出）
│   ├── structured.py      # complete_structured：渲染、呼叫、JSON 驗證、格式重試、併發閘門
│   ├── call_support.py    # 讀取設定快照、組 LiteLLM 參數、錯誤對照、ChatGPT 指示（不含訊息）
│   ├── prompt_loader.py   # 載入、渲染 app/prompts/ 底下的 Jinja2 prompt（StrictUndefined）
│   ├── chat_stream.py     # 測試對話串流：轉成 delta／done／error 事件、確定性關閉上游（不 import litellm）
│   ├── error_messages.py  # 模型服務例外 → 繁中訊息（例外類別由 gateway 傳入，不 import litellm）
│   ├── providers.py       # 服務類型 → LiteLLM 前綴、必填欄位（不 import litellm）
│   ├── config_service.py  # 模型設定的讀寫、使用中切換、變更紀錄
│   ├── system_prompt_service.py  # 共用 system prompt 的版本化儲存
│   ├── model_catalog.py   # 以 httpx 查詢各服務的模型清單、偵測本地伺服器類型（不 import litellm）
│   ├── model_list_parsers.py  # 各服務模型清單 API 的回應格式與解析
│   ├── provider_catalog.py    # 服務類型目錄：顯示名稱、範例、精靈步驟、上限（前端唯一來源）
│   ├── config_summary.py      # 設定摘要文字（已儲存設定與精靈草稿共用）
│   ├── draft_check.py         # 設定精靈的表單檢查（逐欄錯誤、建議名稱、模型查詢方式）
│   ├── model_listing.py   # 查詢可用模型的流程：取得金鑰、過濾對話模型
│   ├── redaction.py       # 服務錯誤說明的金鑰遮蔽
│   ├── chatgpt_auth.py    # ChatGPT 訂閱的裝置碼登入（唯一可 import litellm 內部模組的例外）
│   ├── login_poll_thread.py  # 裝置碼登入的輪詢執行緒：專屬 daemon 執行緒、名額上限（不 import litellm）
├── hospital_data/         # 院方每日資料（只讀、不入庫，見 ADR 0010）
│   ├── source.py          # 唯一開啟院方資料檔的模組：路徑驗證、快取
│   ├── index.py           # 由各日 patientlist 整理病人出現紀錄、統一床號
│   ├── events.py          # 各區塊 → 時間軸紀錄（宣告式欄位對應）
│   ├── labs.py            # 檢驗報告解析、去重、檢驗矩陣
│   ├── timeline.py        # 跨日合併、篩選、依日分組
│   ├── patients.py        # 病房清單、病人清單、病人摘要、原文
│   └── raw_data_service.py  # endpoint 呼叫的入口（同步 I/O 放到 thread）
├── ward_board.py          # 首頁病床總覽：院方讀取（thread）＋批次查詢最新稽核結果
├── ward_board_status.py   # 病床狀態、進度、待處理發現（純函式，不碰 DB）
└── ingestion/
    ├── sources.py         # DataSource Protocol、LocalFixtureSource、RelaySource
    ├── importer.py        # 驗證 → 正規化 → 入庫
    └── normalizers.py
```

- 稽核目前只有單項執行入口：`AuditService.run_rule`（病患頁按鈕與一鍵稽核，經 API 呼叫）與 `get_day_overview`。
- **規劃、尚未實作**：`run_daily_audit(business_date)` 批次入口與排程（ADR 0011 決策 7，排程機制待決）。
- 規則細節見 [audit-rules.md](audit-rules.md)；LLM 見 [llm.md](llm.md)；匯入見 [data-ingestion.md](data-ingestion.md)；流程與稽核週期見 [ADR 0011](../adr/0011-audit-module.md)

### 預期核心資料表

| 表                    | 用途                                                 |
| --------------------- | ---------------------------------------------------- |
| `ingestion_batches`   | 每次匯入的來源、日期、檔案 checksum、狀態            |
| `ingestion_errors`    | 單筆驗證失敗紀錄                                     |
| 病患／紀錄相關表      | **待院方 JSON 格式確定後設計**                       |
| `audit_runs`          | 一次稽核執行：病患、規則、稽核日、狀態、判定、摘要、`details`、模型、prompt 版本、輸入 sha256、token、成本、耗時。重跑新增一列，不覆蓋（ADR 0011） |
| `audit_findings`      | 一次執行中的發現：項目、判定、訊息，以及通過核對的 Evidence（JSON） |
| `llm_configs`         | 使用者設定的模型（API key 加密存放）                 |
| `llm_system_prompts`  | 共用 system prompt，每次儲存為一個新版本             |
| `setting_change_logs` | 設定變更操作紀錄                                     |

## 前端（Next.js App Router 標準結構）

目錄見 [frontend/CLAUDE.md](../../frontend/CLAUDE.md)。

### 頁面（初步）

| 路由                     | 內容                                                                                                                                                               |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `/`                      | 病房地圖：Blender 場景模組依床數組成的 3D 場景搭配病床素材，可拖曳及縮放 50–200%；依最嚴重 Verdict 顯示光暈並篩選（淡化其餘床位）；點選病床於右側（手機為 bottom sheet）顯示病患摘要與稽核結果 |
| `/patients/[patientKey]` | 病患頁面：病患摘要、各規則稽核結果（手動觸發，依稽核日顯示）、Evidence 原文；API 為 `GET /api/v1/patients/{patient_key}/audits`、`POST …/rules/{rule_code}/runs`。前端實作中，以 ADR 0011 為準 |
| `/raw-data`              | 原始資料：左側病人清單（該病房所有日期出現過的病人），右側時間軸（可依起訖日與類別篩選）、檢驗總表（項目 × 採檢時間）、院方原文；狀態全在網址 query，見 [ADR 0010](../adr/0010-hospital-raw-data-viewer.md) |
| `/settings/llm`          | LLM 模型設定：多組設定（同一時間一組使用中）、服務類型、API key（只顯示遮罩值）、ChatGPT 訂閱登入、共用 system prompt、串流測試對話；見 [ADR 0006](../adr/0006-llm-config-settings.md)、[ADR 0007](../adr/0007-llm-system-prompt.md) |

登入後的頁面放在 `app/(workspace)/`，共用工作區外框（頂列、側欄／底部分頁列）；登入頁（待決）之後放在此群組之外。UI 規範見 [ui-design.md](ui-design.md)。

### 資料流

- Server Component 經 `lib/api/` 取資料 → 以 props 傳給 client component 處理互動與動畫
- 資料載入（含錯誤轉成訊息）放在 `lib/api/`，元件只依結果渲染，不在 JSX 外包 try/catch
- 前後端契約以 FastAPI OpenAPI 為準；後端 schema 變更 → 前端 `npm run gen:api`
