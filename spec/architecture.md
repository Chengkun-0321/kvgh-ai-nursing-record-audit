# ① 系統描述

R02 前後紀錄複製／一成不變／時效性稽核（手動觸發版）：使用者在病患頁點某一天的「執行稽核」，後端匯入院內格式的每日資料包（目前為 `mock_data/`），組出當日與前 2 個有資料業務日的紀錄交給 LLM 判斷，結果寫入 DB；病患頁依日期顯示每日稽核結果。

## 技術棧
- 後端：Python 3.12 語法、FastAPI、SQLAlchemy 2.0 async、Pydantic v2、Jinja2、LiteLLM（只在 gateway 使用）
- 前端：Next.js App Router、React、TypeScript、Tailwind CSS
- 測試：後端 pytest（asyncio_mode=auto、記憶體 SQLite）；前端 Vitest＋React Testing Library＋jsdom

## 分層與模組

```
frontend/src/app/(workspace)/patients/[patientKey]/page.tsx（Server Component）
   └→ frontend/src/components/patient-audit/*（呈現、按鈕互動）
        └→ frontend/src/lib/dailyAudit.ts（純函式：卡片狀態、文字格式）
        └→ frontend/src/lib/api/patientAudits.ts（唯一呼叫後端的地方）
                 │ HTTP /api/v1
backend/app/api/v1/endpoints/patient_audits.py（輸入驗證、狀態碼）
   └→ backend/app/services/audit/runner.py（流程編排、交易邊界）
        ├→ services/ingestion/（DataSource → 驗證 → 正規化 → crud 入庫）
        ├→ services/audit/context.py（從 DB 組 AuditContext）
        ├→ services/audit/rules/r02_copy_paste.py（R02：組 prompt 變數、驗證 LLM 輸出、組結果）
        │     └→ StructuredLLM（注入）＝ services/llm/gateway.complete_structured
        └→ crud/ → models/（ingestion_batches、ingestion_errors、admissions、nursing_progress_notes、vital_signs、lab_results、tubes、audit_runs、audit_findings）
```

| 檔案／目錄 | 職責 |
|---|---|
| `backend/app/core/config.py` | 新增 `MOCK_DATA_DIR`（預設為專案根目錄 `mock_data/`）、`RAW_DATA_DIR`（預設 `backend/data/raw/`）、`R02_LOOKBACK_DAYS=2`、`LLM_MAX_RETRIES` |
| `backend/app/core/enums.py` | `Verdict`、`Engine`（不存在就新增，已存在就沿用） |
| `backend/app/core/exceptions.py` | 新增本功能需要的 `AppError` 子類別（找不到病患／日期、不可稽核、未設定模型） |
| `backend/app/schemas/ingestion/` | 院內格式 v0.1.0 的 manifest 與病患檔 Pydantic model（整份驗證） |
| `backend/app/schemas/audit.py` | `Evidence`、`NoteSimilarity`、`AuditFindingRead`、`AuditDayRead`、`AuditDaysRead`、`AuditRunCreate` |
| `backend/app/services/ingestion/sources.py` | `DataSource` Protocol、`LocalFixtureSource` |
| `backend/app/services/ingestion/importer.py` | `import_daily_package()`：保存原始檔 → 驗證 → 正規化 → 入庫 |
| `backend/app/services/audit/base.py` | `AuditRule` Protocol、`AuditContext`、`StructuredLLM` Protocol、Evidence 驗證 helper |
| `backend/app/services/audit/context.py` | 決定比對範圍、從 DB 組 `AuditContext` |
| `backend/app/services/audit/rules/__init__.py` | `RULE_REGISTRY` |
| `backend/app/services/audit/rules/r02_copy_paste.py` | `R02CopyPasteRule` |
| `backend/app/services/audit/runner.py` | `list_audit_days()`、`run_patient_audit()` |
| `backend/app/services/llm/gateway.py` | 新增 `complete_structured()`；既有的測試對話功能不得改變 |
| `backend/app/services/llm/prompt_loader.py` | 載入、渲染 Jinja2 prompt |
| `backend/app/prompts/r02_copy_paste/v1.j2` | R02 prompt（繁中，依 llm.md 的結構） |
| `backend/app/api/v1/endpoints/patient_audits.py` | 兩支 API，掛到 `router.py` |
| `frontend/src/types/patientAudit.ts` | 暫時手寫的 API 型別（收尾時改用 `gen:api` 產生的型別，見「假設」） |
| `frontend/src/components/nursing-records/` | 加上前往病患頁的連結（BR14） |

## 專案固定約束（每次保留，不得刪改）

依據 docs/conventions/architecture.md、audit-rules.md、llm.md、security-privacy.md 與 CLAUDE.md；A1～A3 每次都要有架構測試。CLAUDE.md「核心原則」與 MUST／NEVER 即使未逐條寫進 spec 也必須遵守，由一致性 Agent 檢查。

| 編號 | 約束 | 依據 | 驗證方式 |
|---|---|---|---|
| A1 | `backend/app/` 分層 import 限制：`api/` 不得 import `app.crud`、`app.models`、`app.db`（例外：`api/deps.py` 提供 `get_db`，可 import `app.db`）；`services/` 不得 import `app.api`、`fastapi`；`crud/` 不得 import `app.services`、`app.api`、`app.schemas`；`schemas/` 不得 import `app.models`、`app.crud`、`app.services`；`core/` 在 `app` 內只能 import `app.core` 的模組（標準庫與第三方套件不限） | DIP、分層（architecture.md） | 測試 |
| A2 | `backend/app/` 內只有 `services/llm/gateway.py` 可以 import `litellm`；唯一例外是 `services/llm/chatgpt_auth.py` 可 import `litellm.llms.chatgpt` 底下的模組；整個 `backend/app/` 不得 import `openai`、`anthropic` | LLM 唯一出口（CLAUDE.md、llm.md） | 測試 |
| A3 | `backend/app/services/audit/rules/` 下的檔案不得 import `app.crud`、`app.db`、`httpx`、`sqlalchemy`（規則所需資料由 AuditContext 提供，LLM 由注入的 gateway 呼叫） | 規則無副作用（audit-rules.md） | 測試 |
| A4 | 只實作 audit-rules.md 規則清單內、狀態允許的稽核項目，不新增清單外的判斷 | 不自行發明稽核規則（CLAUDE.md） | 審查 |
| A5 | 稽核訊息使用「…不一致／未見紀錄，請確認」的提醒語氣，不得出現 audit-rules.md「訊息用語」表禁止欄的措辭 | 不一致 ≠ 錯誤（CLAUDE.md） | 審查 |
| A6 | log、例外訊息、API 錯誤回應不得包含姓名、病歷號、身分證字號、生日、電話、地址、紀錄全文；涉及病患時只以 `patient_key`、`record_id`、規則代碼、批次 ID 識別（與病患無關的操作紀錄不受此限） | security-privacy.md「Log 與錯誤訊息」 | 審查 |
| A7 | 註解、docstring、UI 文字使用繁體中文；識別字用英文 | CLAUDE.md | 審查 |

## 架構約束（本次功能，從 A8 起編）

| 編號 | 約束 | 依據 | 驗證方式 |
|---|---|---|---|
| A8 | R02 定義為 `backend/app/services/audit/rules/r02_copy_paste.py` 的 `R02CopyPasteRule`，滿足 `AuditRule` Protocol（`code="R02"`、`engine=Engine.LLM`），並登錄在 `RULE_REGISTRY["R02"]`；`runner.py` 不得出現字串 `"R02"` 或 `R02CopyPasteRule`，一律經 `RULE_REGISTRY` 取得規則（API 預設值 `"R02"` 放在 schema） | Strategy、OCP | 測試（registry 內容、掃描 runner 原始碼）＋審查 |
| A9 | `services/ingestion/importer.py` 只依賴 `DataSource` Protocol，不得出現 `LocalFixtureSource`；`backend/app/` 中只有 `services/ingestion/sources.py` 可以開啟 `MOCK_DATA_DIR` 底下的檔案 | DIP | 測試（掃描 importer 原始碼）＋審查 |
| A10 | `backend/app/services/audit/rules/` 下的檔案不得 import `app.services.ingestion`、`app.services.llm.gateway`；規則透過注入的 `StructuredLLM` Protocol 呼叫 LLM | DIP | 測試 |
| A11 | R02 的 `message` 只由 `r02_copy_paste.py` 內的訊息模板常數組成（可代入日期、時間、record_id、百分比），不得直接放入 LLM 回傳的自由文字 | 不一致 ≠ 錯誤、可預測性 | 審查（並由 BR9 的測試檢查輸出） |
| A12 | R02 prompt 位於 `backend/app/prompts/r02_copy_paste/v1.j2`，只經 `services/llm/prompt_loader.py` 渲染；結果的 `prompt_version` 為 `"r02_copy_paste/v1"` | llm.md「Prompt 規範」 | 測試 |
| A13 | `frontend/src/components/patient-audit/` 與 `frontend/src/app/(workspace)/patients/` 下的檔案不得出現 `fetch(`；後端呼叫只放在 `frontend/src/lib/api/patientAudits.ts` | SRP、frontend/CLAUDE.md | 測試 |
| A14 | 每日卡片的狀態判斷（不可稽核／未稽核／已稽核）、相似度文字與日期的格式化，都在 `frontend/src/lib/dailyAudit.ts` 的純函式完成，元件不自行判斷 | SRP | 審查 |

## 對外介面

後端：
```python
# app/core/enums.py
class Verdict(StrEnum): PASS, WARNING, ERROR, NEEDS_REVIEW
class Engine(StrEnum): RULE="rule", LLM="llm", HYBRID="hybrid"

# app/services/ingestion/sources.py
class DataSource(Protocol):
    def list_business_dates(self) -> list[date]: ...                      # 名稱合法（YYYYMMDD）的資料夾
    async def fetch_manifest(self, business_date: date) -> RawDocument: ...
    async def fetch(self, business_date: date) -> list[RawDocument]: ...  # manifest＋病患檔
class LocalFixtureSource:
    def __init__(self, root: Path): ...

# app/services/llm/gateway.py
class LLMOutputError(Exception): ...
async def complete_structured(request: LLMRequest, output_schema: type[T]) -> LLMResult[T]: ...

# app/services/audit/base.py
class StructuredLLM(Protocol):
    async def __call__(self, request: LLMRequest, output_schema: type[T]) -> LLMResult[T]: ...

# app/services/audit/runner.py
async def list_audit_days(session: AsyncSession, source: DataSource, patient_key: str) -> AuditDaysRead: ...
async def run_patient_audit(session: AsyncSession, source: DataSource, llm: StructuredLLM,
                            patient_key: str, business_date: date, rule_code: str) -> AuditFindingRead: ...
```
- 測試以 `from app.main import app` 取得 FastAPI app，並以 dependency override 注入兩樣東西：指向 `tmp_path` 的 `LocalFixtureSource`、假的 `StructuredLLM`。
- API 欄位見 boundaries.md 的 B1、B2。

前端：
```ts
// src/lib/api/patientAudits.ts
export async function getAuditDays(patientKey: string): Promise<AuditDays>
export async function runAudit(patientKey: string, businessDate: string): Promise<AuditFinding>
// src/lib/dailyAudit.ts
export type DayCardState = "not_auditable" | "not_run" | "done"
export function dayCardState(day: AuditDay): DayCardState
export function sortDaysDesc(days: AuditDay[]): AuditDay[]
export function formatSimilarity(note: NoteSimilarity): string
//   例：「今日 09:30 紀錄（NPN-B-0904-01）與 9/03 紀錄（NPN-B-0903-01）相似 98.0%（模型估計）」
export function auditButtonLabel(day: AuditDay, running: boolean): string | null
// src/components/patient-audit/DailyAuditList.tsx
export function DailyAuditList(props: { patientKey: string; days: AuditDay[];
  runAudit: (patientKey: string, businessDate: string) => Promise<AuditFinding> }): JSX.Element
```
- 測試以 `@/lib/...`、`@/components/patient-audit/...` 匯入；`DailyAuditList` 以 props 注入假的 `runAudit`。

## 技術決策（由 /spec-draft 決定，人看過即可）
- DB：新增上述資料表，型別遵守 ADR 0001（`DateTime(timezone=True)`、`Uuid`、`JSON`、`native_enum=False`）。migration 由人在流程結束後以 Alembic 產生，流程角色不寫 `alembic/`。
- 不新增套件：Jinja2、LiteLLM 已核准；相似度由 LLM 估計，不用程式計算。
- 測試檔位置：
  - 後端：`backend/tests/architecture/`、`backend/tests/services/audit/`、`backend/tests/services/ingestion/`、`backend/tests/services/llm/test_gateway_structured.py`、`backend/tests/api/v1/test_patient_audits_api.py`、`backend/tests/fixtures/daily_packages/`
  - 前端：`frontend/tests/lib/dailyAudit.test.ts`、`frontend/tests/lib/api/patientAudits.test.ts`、`frontend/tests/components/patient-audit/`
- 測試資料：自製最小虛構資料包（2～3 個業務日、1～2 位病患），不讀 `mock_data/`。
- 允許的套件：見 `flow.config.json` 的 `deps_check`。
- 執行方式：由流程依 `setup_command`、`test_command` 執行（AI 不直接執行）。
