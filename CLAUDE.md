# 高榮 AI 護理紀錄稽核系統（kvgh-ai-nursing-record-audit）

使用 LLM 稽核護理師紀錄（入院護理評估、每日身體評估、過程紀錄、轉入／轉出摘要、給藥紀錄…）的完整性與一致性。
流程：讀取院方病房資料 → 依稽核週期執行稽核規則（目前手動觸發）→ 產出附 Evidence 的稽核結果 → 護理師／護理長確認。

> 目前階段：**領域運算與驗證一律在後端，前端只渲染**（[ADR 0009](docs/adr/0009-backend-owns-computation.md)）。
> - **稽核模組已實作**（[ADR 0011](docs/adr/0011-audit-module.md)）：R01–R04、R06 可執行；R05、R07 為預留（院方資料不足，回「院方尚未提供資料」）。結果存入 `audit_runs`／`audit_findings`，病患頁手動觸發（單項與一鍵稽核）。稽核日必須已結束、R06 截至所選稽核日逐筆追蹤會診、（[ADR 0012](docs/adr/0012-audit-day-rules.md)）；入院規則（R01、R03）完成後可單項重新稽核、一鍵稽核不納入（[ADR 0013](docs/adr/0013-admission-rule-rerun.md)）。
> - 首頁預設病患清單，每列顯示 R01–R07 七項稽核狀態，可切換 3D 病房並記住偏好（[ADR 0014](docs/adr/0014-home-patient-list.md)）；床位整體狀態與「已稽核 N／M 項」進度沿用 [ADR 0011](docs/adr/0011-audit-module.md) 決策 8。
> - **尚未做**：排程與整個病房的批次稽核；中繼站匯入（`services/ingestion`）。
> - 院方資料（根目錄 `data/` 的去識別化資料）由後端直接讀檔、不入庫，見 [ADR 0010](docs/adr/0010-hospital-raw-data-viewer.md)。首頁顯示院方 W63 病房；可切換的滿版 3D 病房沿用 Blender 場景模組＋React Three Fiber。`/raw-data` 原始資料頁以時間軸、檢驗總表、原文檢視各病人所有日期的資料。
> - LLM 模型設定見 [ADR 0006](docs/adr/0006-llm-config-settings.md)、[ADR 0007](docs/adr/0007-llm-system-prompt.md)。

## 核心原則（領域）

1. **只提醒，不修改**：系統不得寫回或修改任何病歷資料。
2. **每個判定都要有 Evidence**：來源、紀錄 ID、欄位、日期、原文片段；沒有 Evidence 不得輸出異常。
3. **不一致 ≠ 錯誤**：訊息用「…不一致／未見紀錄，請確認」，禁止「護理師寫錯」這類措辭。
4. **LLM 判定，程式核對**：七項稽核一律經 LLM 判定；程式只整理事實、核對 Evidence、驗證輸出結構，不下判定（[ADR 0011](docs/adr/0011-audit-module.md)）。取代舊的「Rule 優先，LLM 其次」。
5. **不自行發明稽核規則**：只實作 [audit-rules.md](docs/conventions/audit-rules.md) 清單內的項目。

## 技術棧

| 層 | 技術 |
|---|---|
| 前端 | Next.js（App Router）+ React + TypeScript + Tailwind CSS + Framer Motion；病房場景用 three.js + React Three Fiber，模組由 Blender 腳本產生 |
| 後端 | FastAPI + SQLAlchemy 2.0（async）+ Alembic + Pydantic v2 |
| LLM | LiteLLM（唯一出口，模型由使用者於網頁設定） |
| DB | SQLite（開發）→ PostgreSQL（正式），程式必須兩者皆可運作 |
| 環境 | Python `venv` + `pip`、Node `npm`；**所有套件只裝在專案內，不裝任何全域工具** |

## MUST

- 動手前先讀「文件索引」中與任務相關的文件
- 變更超過 3 個檔案，或涉及 DB schema／prompt／稽核規則邏輯時，先提出計畫再實作
- 所有 LLM 呼叫只經 `backend/app/services/llm/gateway.py`
- 門檻值、模型名稱、路徑等放 settings 或常數，不寫死
- 領域命名依 [glossary.md](docs/glossary.md)；出現新詞彙先補進詞彙表
- 文件、註解、docstring、commit message、UI 文字一律**繁體中文**；識別字（變數、函式、類別、檔名）用英文
- 遇到「待決事項」時停下來詢問，不自行假設

## NEVER

- 直接 import `openai`、`anthropic` 等模型 SDK（一律經 LiteLLM gateway）
- 全域安裝：`pip install --user`、`sudo pip`、`npm -g`、`brew install`、`corepack enable` 等
- commit `.env`、API key、`backend/data/` 或任何病患資料
- 在 log、例外訊息輸出姓名、病歷號、身分證字號等識別資料
- 未經同意新增依賴（核准清單見 [backend/CLAUDE.md](backend/CLAUDE.md)、[frontend/CLAUDE.md](frontend/CLAUDE.md)）
- 修改與任務無關的程式碼；修改已 commit 的 Alembic migration
- 未經使用者要求執行 `git commit`／`git push`

## 目錄

```
├── backend/          # FastAPI 標準結構 → backend/CLAUDE.md
├── frontend/         # Next.js App Router 標準結構 → frontend/CLAUDE.md
└── docs/
    ├── conventions/  # 各主題規範
    ├── glossary.md   # 領域詞彙中英對照
    └── adr/          # 架構決策紀錄
```

## 文件索引（依任務讀取）

| 任務 | 必讀 |
|---|---|
| Docker 容器化與 Linux 部署 | [deployment-docker.md](docs/deployment-docker.md) |
| 任何程式撰寫 | [clean-code.md](docs/conventions/clean-code.md)、[architecture.md](docs/conventions/architecture.md) |
| 前端 UI、樣式、動畫 | [ui-design.md](docs/conventions/ui-design.md)（依據 `.claude/skills/apple-design`、`.claude/skills/ui-ux-pro-max`） |
| 新增／修改稽核規則 | [audit-rules.md](docs/conventions/audit-rules.md)、[llm.md](docs/conventions/llm.md) |
| 稽核流程、稽核週期、執行狀態 | [ADR 0011](docs/adr/0011-audit-module.md)、[architecture.md](docs/conventions/architecture.md) |
| LLM 呼叫、prompt、模型設定 | [llm.md](docs/conventions/llm.md)、[security-privacy.md](docs/conventions/security-privacy.md) |
| 資料匯入（院方 JSON／中繼站）、原始資料頁 | [data-ingestion.md](docs/conventions/data-ingestion.md)、[ADR 0010](docs/adr/0010-hospital-raw-data-viewer.md) |
| DB schema、migration | [backend/CLAUDE.md](backend/CLAUDE.md)、[ADR 0001](docs/adr/0001-sqlite-to-postgresql.md) |
| 撰寫測試 | [testing.md](docs/conventions/testing.md) |
| commit、branch | [git-workflow.md](docs/conventions/git-workflow.md) |
| 記錄架構決策 | [docs/adr/README.md](docs/adr/README.md) |

## 常用指令（初始化後適用）

一鍵啟動／關閉前後端（於專案根目錄；背景執行，PID 與 log 在 `.run/`，實作見 `scripts/dev.sh`）：

```bash
npm start
```

```bash
npm stop
```

`npm run status` 查看狀態、`npm run restart` 重啟。各分支的 migration 不同時，用 `DEV_DB_NAME=<名稱> npm start` 改用 `backend/data/<名稱>.db`（`npm run start:main` 即 `main.db`）。

後端（於 `backend/`，先 `source .venv/bin/activate`）：

```bash
uvicorn app.main:app --reload
```

```bash
ruff check . && ruff format --check . && mypy app
```

```bash
alembic revision --autogenerate -m "描述" && alembic upgrade head
```

前端（於 `frontend/` 根目錄執行，讓 npm 快取留在專案內）：

```bash
npm run dev
```

```bash
npm run lint && npm run typecheck
```

```bash
npm run gen:api
```

## Definition of Done

- lint、format、type check 全數通過
- 既有測試不壞（測試非強制，但有寫就必須通過）
- DB schema 變更附 Alembic migration
- 新詞彙／新決策／新規則已同步到 glossary、ADR、audit-rules.md

## 待決事項（遇到時先詢問，不自行假設）

- 院方 JSON 資料格式、中繼站傳輸方式與認證
- Verdict 分級（暫定 `PASS` / `WARNING` / `ERROR` / `NEEDS_REVIEW`；目前 LLM 最高只到 `WARNING`，`ERROR` 沒有產生來源）
- R06 追蹤期限天數（每筆會診日加 `AUDIT_CONSULT_FOLLOWUP_DAYS` 為到期日，暫定 1；院方沒有簽收與回覆時間；見 [ADR 0012](docs/adr/0012-audit-day-rules.md) 決策 2）
- R04 是否把「跌倒危險」「移動能力」視為需要追蹤的異常項目（程式目前不排除；`audit-rules.md` 原列「防跌」為排除項目）
- R05、R07 所需的院方資料：轉出／轉入摘要、給藥執行紀錄
- R01、R03 的選項清單與「不適用」狀態
- 夜間批次排程機制
- 正式的使用者登入與權限（目前為 demo 固定帳密，見 [ADR 0015](docs/adr/0015-demo-login.md)）
- 候選稽核項目（R08–R11）是否納入第一版
- 接真實資料後的 PHI 外送政策（見 [ADR 0002](docs/adr/0002-llm-phi-policy.md)）
