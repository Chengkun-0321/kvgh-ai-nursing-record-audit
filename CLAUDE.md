# 高榮 AI 護理紀錄稽核系統（kvgh-ai-nursing-record-audit）

使用 LLM 稽核護理師紀錄（入院護理評估、每日身體評估、過程紀錄、轉入／轉出摘要、給藥紀錄…）的完整性與一致性。
流程：每日讀取病房資料 → 執行稽核規則 → 產出附 Evidence 的稽核結果 → 護理師／護理長確認。

> 目前階段：`frontend/` 已初始化，Apple 風格工作區與首頁病床總覽（Blender 場景模組＋React Three Fiber 的滿版 3D 病房，預設正視、可切換斜視）仍使用前端假資料（`src/lib/api/`）。`backend/` 已初始化 FastAPI 骨架與 LLM 模型設定（`/settings/llm`：多組設定、ChatGPT 訂閱登入、共用 system prompt、串流測試對話，見 [ADR 0006](docs/adr/0006-llm-config-settings.md)、[ADR 0007](docs/adr/0007-llm-system-prompt.md)）。院方每日資料格式已先定義（[hospital-data-spec.md](docs/hospital-data-spec.md)、[ADR 0009](docs/adr/0009-hospital-daily-data-format.md)），根目錄 `mock_data/` 為 4 位病患 9/01–9/30 的虛構每日資料包（含正確／錯誤情境答案表），可在桌機導覽「護理紀錄」頁（`/nursing-records`）瀏覽（[ADR 0010](docs/adr/0010-mock-data-viewer.md)）；資料匯入與稽核規則尚未實作。

## 核心原則（領域）

1. **只提醒，不修改**：系統不得寫回或修改任何病歷資料。
2. **每個判定都要有 Evidence**：來源、紀錄 ID、欄位、日期、原文片段；沒有 Evidence 不得輸出異常。
3. **不一致 ≠ 錯誤**：訊息用「…不一致／未見紀錄，請確認」，禁止「護理師寫錯」這類措辭。
4. **Rule 優先，LLM 其次**：可用程式判斷的（欄位完整性、日期、次數）不交給 LLM。
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
├── mock_data/        # 虛構病房每日資料包（YYYYMMDD/manifest.json＋每位病患一檔），答案表見 README
└── docs/
    ├── conventions/  # 各主題規範
    ├── glossary.md   # 領域詞彙中英對照
    ├── hospital-data-spec.md  # 院方每日資料交換格式（交給資訊處）＋ hospital-data-spec/*.schema.json
    └── adr/          # 架構決策紀錄
```

## 文件索引（依任務讀取）

| 任務 | 必讀 |
|---|---|
| 任何程式撰寫 | [clean-code.md](docs/conventions/clean-code.md)、[architecture.md](docs/conventions/architecture.md) |
| 前端 UI、樣式、動畫 | [ui-design.md](docs/conventions/ui-design.md)（依據 `.claude/skill/apple-design`、`.claude/skill/ui-ux-pro-max`） |
| 新增／修改稽核規則 | [audit-rules.md](docs/conventions/audit-rules.md)、[llm.md](docs/conventions/llm.md) |
| LLM 呼叫、prompt、模型設定 | [llm.md](docs/conventions/llm.md)、[security-privacy.md](docs/conventions/security-privacy.md) |
| 資料匯入（假資料／中繼站 JSON） | [data-ingestion.md](docs/conventions/data-ingestion.md)、[hospital-data-spec.md](docs/hospital-data-spec.md)、[mock_data/README.md](mock_data/README.md) |
| DB schema、migration | [backend/CLAUDE.md](backend/CLAUDE.md)、[ADR 0001](docs/adr/0001-sqlite-to-postgresql.md) |
| 撰寫測試 | [testing.md](docs/conventions/testing.md) |
| commit、branch | [git-workflow.md](docs/conventions/git-workflow.md) |
| 記錄架構決策 | [docs/adr/README.md](docs/adr/README.md) |

## 常用指令（初始化後適用）

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
- Verdict 分級（暫定 `PASS` / `WARNING` / `ERROR` / `NEEDS_REVIEW`）
- 複製紀錄相似度門檻（80% 或 90%）
- 夜間批次排程機制、使用者登入與權限
- 候選稽核項目（R08–R11）是否納入第一版
- 接真實資料後的 PHI 外送政策（見 [ADR 0002](docs/adr/0002-llm-phi-policy.md)）
