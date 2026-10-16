# 規格驅動開發流程（/spec-draft → /senior-flow）

上游流程原文見 [spec-flow-upstream.md](../spec-flow-upstream.md)；本文件只寫本專案的用法與差異。決策理由見 [ADR 0012](../adr/0012-spec-driven-flow.md)。

## 何時使用

| 適合 | 不適合（照一般方式開發） |
|---|---|
| 規格能寫成「給定輸入 → 預期結果」的功能：稽核規則的程式判斷、資料匯入的驗證與正規化、API 合約、前端的純邏輯（`lib/`） | 視覺與互動調整（3D 場景、動畫、版面）、需要邊做邊試的探索、只改文件 |
| 範圍可以縮到少數目錄的功能 | 需要同時改 `alembic/`、lint／型別設定、`requirements-dev.txt` 的工作 |

## 步驟

```text
1. /spec-draft <用 Design Patterns／SOLID／邊界／業務規則描述需求>   ← 回答反問，確認草稿後寫入 spec/
2. ! bash .claude/flow/approve_spec.sh                                ← 只能由人執行
3. /senior-flow                                                       ← agent 寫程式、寫測試、跑測試、出報告，停在人審
4. 看 .flow/report.md，再做下面的「收尾清單」
```

## 規格編號

| 編號 | 檔案 | 意義 | 驗證 |
|---|---|---|---|
| A1～A7 | `spec/architecture.md` | 專案固定約束（分層 import、LLM 只經 gateway、規則無副作用、只做清單內稽核項目、提醒語氣、不輸出識別資料、繁中），每次保留 | A1～A3 測試；A4～A7 審查 |
| A8 起 | `spec/architecture.md` | 本次功能的架構約束 | 測試或審查 |
| B* | `spec/boundaries.md` | 系統邊界、API 合約 | 合約測試或審查 |
| BR*、E* | `spec/rules.md` | 業務規則、異常行為 | 測試 |

`R01`～`R11` 是稽核項目代碼（[audit-rules.md](audit-rules.md)），不是規格編號。上游流程用 `R*` 表示業務規則，本專案改成 `BR*` 避免混淆。

## 角色可讀寫範圍

路徑都來自 `flow.config.json`。

| 角色 | 可讀 | 可寫 |
|---|---|---|
| 主對話、其他 subagent（流程**沒在跑**） | 整個專案 | 整個專案（`.approved` 除外） |
| 主對話（流程執行中） | spec、`.flow/`、`flow.config.json`、`.claude/flow/`、`examples/` | 無；Bash 只能單獨執行 `bash .claude/flow/<名稱>.sh [輪次]` |
| prompt-builder | spec、`reference_paths`、`.flow/prompts/`、`.flow/runs/`、`.flow/report.md` | `.flow/prompts/` |
| coder | spec、`reference_paths`、`.flow/prompts/coder.md`、`src_dirs`、`coder_read_paths` | `src_dirs` |
| test-designer | spec、`reference_paths`、`.flow/prompts/tester.md`、`test_dirs`、`tester_read_paths` | `test_dirs` |
| consistency-checker | 整個專案 | 無 |

- 不論流程是否在跑，AI 都不能執行 `approve_spec.sh`、`state.py approve`，也不能寫入 `.approved`。Bash 以 shlex 切出每段簡單指令後判斷（處理引號、`-x` 等選項、`$(…)`、反引號、換行、`;`／`&&`／管線）：
  - 擋：腳本出現在執行位置（例如 `bash -x ".claude/flow/approve_spec.sh"`）、`python3 … state.py approve`，以及透過 `>`／`>>`、`tee`／`touch`／`rm`，或 `cp`／`mv`／`ln`／`install` 的**目的地**寫入 `.approved`。
  - 不擋：`cat spec/.approved`、`cp spec/.approved /tmp/x`（只是來源）、`git diff -- .claude/flow/approve_spec.sh`、引號內的文字。
  - heredoc：加引號的（`<<'EOF'`）內容視為資料；未加引號的會執行命令替換，所以其中的 `$(…)`、反引號仍會分析。
- 路徑設定結尾有 `/` 的是目錄，沒有 `/` 的是單一檔案（精確比對）。搜尋（Grep／Glob）目錄時，單一檔案的設定不算數，因為 Grep 會遞迴。
- Glob 依 `path` 加上 pattern 在萬用字元之前的目錄判斷實際搜尋範圍，pattern 寫成絕對路徑或含 `..` 也一樣檢查；沒有萬用字元時就是指定的那個路徑。
- `approve_spec.sh` 和 `flow_init.sh` 會執行 `state.py check_config`。下列情況會拒絕：
  - test-designer 可讀的路徑碰到程式（`src_dirs`、`coder_read_paths`）
  - coder 可讀的路徑碰到測試
  - `src_dirs` 與 `test_dirs` 重疊
  - `src_dirs` 或 `test_dirs` 設成專案根目錄
  - 可寫範圍包含流程控制檔：規格目錄、`flow.config.json`、`.claude/`、`.flow/`、`.git/`（不論有沒有尾斜線）
  - 實際是目錄的設定沒加尾斜線

  有效讀取範圍與 guard 相同，規格目錄與 `reference_paths` 也一起算。

## flow.config.json 的本專案預設

`/spec-draft` 會依功能把 `src_dirs`、`test_dirs` 縮到最小，其餘欄位沿用預設。

| 欄位 | 預設 | 理由 |
|---|---|---|
| `src_dirs` | `backend/app/`、`backend/requirements.txt`、`frontend/src/`、`frontend/package.json` | coder 能產生套件檔 |
| `test_dirs` | `backend/tests/`、`frontend/tests/`、`frontend/vitest.config.mts` | 測試設定歸測試角色 |
| `coder_read_paths` | `backend/app/`、`frontend/src/` | `src_dirs` 縮小後，coder 仍需讀 gateway、`db/base.py` 等既有模組 |
| `tester_read_paths` | 空 | `test_dirs` 縮小時放入 `backend/tests/conftest.py` |
| `reference_paths` | 三份 CLAUDE.md、`docs/conventions/`、`docs/glossary.md`、`docs/adr/`、`docs/hospital-data-spec*`、`mock_data/README.md` | 流程角色設了 `omitClaudeMd`，專案規範改由這裡讀取；CLAUDE.md 要求必讀的 ADR 也要讀得到 |
| `deps_check` | `backend/requirements.txt`、`frontend/package.json`，白名單為兩份 CLAUDE.md 的核准依賴 | 新增依賴要先經人同意，再加進白名單 |
| `setup_command` | 用 `backend/.venv` 安裝 `requirements-dev.txt`，接著用 ruff format／`ruff check --fix` 格式化；`npm install --legacy-peer-deps`，接著用 prettier 格式化 | 只裝在專案內；格式由腳本處理，coder 不必猜。各段以 `&&` 串接，安裝失敗就整輪失敗；只有 `ruff check --fix` 允許失敗（剩下的問題由 `test_command` 回報） |
| `test_command` | 後端：pytest → ruff check → ruff format --check → mypy。前端：vitest → eslint → tsc | 等同 Definition of Done 的 lint／型別檢查；直接呼叫工具，不經 `npm run`，避免 coder 改 scripts 繞過 |

不放進任何可寫範圍的檔案：
- `backend/alembic/`、`backend/requirements-dev.txt`、`backend/pyproject.toml`、`frontend/eslint.config.mjs`

原因：
- coder 不能放寬 lint、型別、測試設定。
- migration 由人在流程結束後產生。
- `requirements-dev.txt` 首行的 `-r requirements.txt` 會被白名單檢查判為違規，因此也不列入 `deps_check`。

## 收尾清單（流程結束後，由主對話執行）

流程結束後 `status` 不是 `running`，主對話不再受 guard 限制。

1. 有 model 變更：在 `backend/` 執行 `alembic revision --autogenerate -m "繁中描述"`，人工檢查產出後 `alembic upgrade head`。
2. 同步 `docs/glossary.md`、ADR、`audit-rules.md`。
3. 檢查 `frontend/package-lock.json` 的 diff：`setup_command` 的 `npm install --legacy-peer-deps` 會改寫 lock，套件有變動時應 commit；只有 `dev`／`devOptional` 標記變動時可還原。
4. 與 Codex 互審本次 diff。
5. 跑完整 Definition of Done 檢查。
6. 使用者要求時才 commit；`spec/`、`spec/.approved` 和程式放同一個 commit。

## 已知限制

- **Bash 的確認檢查只防誤操作，不是安全邊界。** 依指令結構判斷，`python -c`、`eval`、變數組字串、把指令放進加引號的 heredoc 再交給 shell 等刻意改寫的方式仍可能繞過。
- **專案規範的優先順序。** CLAUDE.md「核心原則」與 MUST／NEVER 優先於 spec，一致性報告第 3.5 節逐條判定，違反就是「不一致」；其他規範以 spec 為準，違反列在第 6 節。
- **真實 subagent 的 hook 整合尚未實測。** 測試以模擬的 `agent_type` 呼叫 guard，第一次跑 `/senior-flow` 時要看 `.flow/audit.jsonl` 確認角色判定正確。
- **隔離只在 hooks 啟用時有效。** `.claude/settings.local.json` 不得放 `{"disableAllHooks": true}`。
- **流程中斷時 spec 會一直鎖住。** `.flow/state.json` 停在 `running` 時，由人刪除 `.flow/` 解鎖。
- **重跑前要視需要自行清理程式與測試目錄。** 每次 `/senior-flow` 會清掉 `.flow/`，但不會清這兩個目錄。
- **A4～A7（審查類）屬於 AI 判斷。** 需要硬性保證的約束，要寫成「測試」類。
- **每輪的 `setup_command` 會連網安裝套件。** pip 與 npm 的快取都留在專案內。
