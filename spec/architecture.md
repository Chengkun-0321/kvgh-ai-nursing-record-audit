# ① 系統描述（人描述，/spec-draft 整理）

<!--
填寫說明：
- 人用軟工語言描述系統：分層／模組、Design Patterns、SOLID 約束、技術棧。
- 每條約束編號 A1、A2…，並標註驗證方式：
  - 測試：可以寫成自動測試（例如「app/routers/ 下的檔案不得 import app/db」→ 掃描 import）
  - 審查：由一致性 Agent 讀程式判定，必須寫成可判斷的句子（不能只寫「遵守 SRP」）
- 程式檔必須在 flow.config.json 的 src_dirs 內，測試檔必須在 test_dirs 內。
- 範例見 examples/react-fastapi/architecture.md、examples/discount/architecture.md。
-->

## 技術棧
- （待填：語言與版本、框架）

## 分層與模組
- （待填：例如 `backend/app/routers/` → `backend/app/services/` → `backend/app/domain/`）

## 架構約束（Design Patterns／SOLID）

| 編號 | 約束 | 依據 | 驗證方式 |
|---|---|---|---|
| A1 | （待填） | （例如 Strategy、DIP） | 測試／審查 |

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
