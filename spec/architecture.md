# ① 系統描述（人描述，/spec-draft 整理）

<!--
填寫說明：
- 人用軟工語言描述系統：分層／模組、Design Patterns、SOLID 約束、技術棧。
- 「專案固定約束」A1～A7 每次保留；本次功能的約束從 A8 起編，並標註驗證方式：
  - 測試：可以寫成自動測試（例如「app/routers/ 下的檔案不得 import app/db」→ 掃描 import）
  - 審查：由一致性 Agent 讀程式判定，必須寫成可判斷的句子（不能只寫「遵守 SRP」）
- 程式檔必須在 flow.config.json 的 src_dirs 內，測試檔必須在 test_dirs 內。
- 範例見 examples/react-fastapi/architecture.md、examples/discount/architecture.md。
-->

## 技術棧
- （待填：語言與版本、框架）

## 分層與模組
- （待填：例如 `backend/app/routers/` → `backend/app/services/` → `backend/app/domain/`）

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
| A8 | （待填） | （例如 Strategy、DIP） | 測試／審查 |

## 對外介面
```
（待填：函式／類別／API 簽名）
```
- （待填：測試要如何匯入或呼叫）

## 技術決策（由 /spec-draft 決定，人看過即可）
- 設定檔：（待填，例如 package.json 由 coder 產生）
- 允許的套件：見 `flow.config.json` 的 `deps_check`
- 測試檔：（待填）
- 執行方式：由流程依 `flow.config.json` 的 `setup_command`、`test_command` 執行（AI 不直接執行）。
