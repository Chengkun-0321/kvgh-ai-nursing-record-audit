> **本專案註記**：本檔為上游流程的原始說明，保留作為參考。本專案做了調整（guard 只在流程中限制、`reference_paths`、`BR*` 編號、前端測試位置、安裝只用 `.venv`），以 [conventions/spec-flow.md](conventions/spec-flow.md) 為準。

# 學長方法開發流程（Claude Code 版）

## 人只做三件事

1. **系統描述**：以軟工角度描述系統，包含分層、Design Patterns、SOLID 約束 → `spec/architecture.md`（編號 A*）
2. **邊界**：System Boundaries → `spec/boundaries.md`（B*）；Business Rules → `spec/rules.md`（R*、E*）
3. **看報告**：確認規格（`approve_spec.sh`），最後只看一致性 Agent 的報告

其餘工作全部由 agent 完成：反問與整理規格、決定技術細節（檔名、設定檔、套件、測試指令）、寫程式與專案設定檔、寫測試與測試設定、安裝、跑測試、比對一致性。
框架與語言、目錄結構無關，專案差異全部寫在 `flow.config.json` 與 `spec/`；`flow.config.json` 也由 `/spec-draft` 產生。

| 編號 | 來源 | 驗證 |
|---|---|---|
| A* | 系統描述（Design Patterns／SOLID） | 每條標「測試」（架構測試，例如掃描 import）或「審查」（一致性 Agent 讀程式判定） |
| B* | 系統邊界 | 合約測試或審查 |
| R*、E* | 業務規則與異常行為 | 測試 |

## 流程

| 步驟 | 實作 |
|---|---|
| ⓪ 需求釐清 | `.claude/skills/spec-draft/SKILL.md`（`/spec-draft`）：只反問設計與業務問題，技術細節自行決定；寫入 `spec/` 與 `flow.config.json` |
| ①② 人確認規格 | `spec/architecture.md`、`spec/boundaries.md`、`spec/rules.md`；人執行 `approve_spec.sh` 產生 `spec/.approved` |
| 指揮 | `.claude/skills/senior-flow/SKILL.md`（`/senior-flow`） |
| ③ Prompt Builder | `.claude/agents/prompt-builder.md` → `.flow/prompts/` |
| ④ Coding Agent | `.claude/agents/coder.md` → `src_dirs`（程式＋專案設定檔、套件檔），讀不到測試 |
| ⑤ Test Design Agent | `.claude/agents/test-designer.md` → `test_dirs`（測試＋測試設定檔），讀不到程式 |
| ⑥ 跑測試 | `.claude/flow/run_tests.sh`（不經 AI）：套件白名單檢查 → `setup_command` → `test_command`，任一段失敗即該輪失敗 → `.flow/runs/round-N.log` |
| ⑦ 一致性 Agent | `.claude/agents/consistency-checker.md`（唯讀），報告給不看程式碼的人看（摘要、A／B／R／E 對照、套件、規格本身的問題），由 `capture_report.py` 存成 `.flow/report.md` |
| ⑧ 人審 | 流程停下，交出報告 |

守門：`.claude/hooks/guard.py`（PreToolUse，依角色與 `flow.config.json` 的目錄限制讀寫，紀錄在 `.flow/audit.jsonl`）、`stop_guard.py`（流程未完成不准結束）。

### spec 確認關卡

- `/spec-draft` 只有在流程沒在跑時能寫 `spec/` 與 `flow.config.json`；流程執行中兩者鎖定，任何 AI 角色都改不了。
- `approve_spec.sh` 會把 `architecture.md`、`boundaries.md`、`rules.md`、`flow.config.json`（含套件白名單）的雜湊記到 `spec/.approved`。guard 禁止 AI 執行這支腳本或寫入 `.approved`，只能由人執行。
- `/senior-flow` 開始時檢查雜湊：未確認、或確認後內容被改過，就拒絕開始。
- `spec/.approved` 建議和 spec 一起 commit，留下「哪一版規格經人確認」的紀錄。
- 流程中斷導致 `.flow/state.json` 停在 running 時，spec 會一直鎖定；人刪除 `.flow/` 即可解鎖。

## 套用到其他專案

### 1. 複製

```bash
TARGET=/path/to/your-project
mkdir -p "$TARGET/.claude"
cp -r .claude/agents .claude/hooks .claude/skills .claude/flow "$TARGET/.claude/"
cp flow.config.json "$TARGET/"
cp -r spec "$TARGET/"                       # 空白範本
[ -f "$TARGET/.claude/settings.json" ] || cp .claude/settings.json "$TARGET/.claude/"
```

不要複製 `.claude/settings.local.json`（個人設定）、`examples/`、`.flow/`。

### 2. 目標專案已有 `.claude/settings.json` 時手動合併

把下列內容併進既有檔案（`permissions.allow` 與 `hooks` 底下的陣列用附加的方式，不要覆蓋原有項目）：

```json
{
  "permissions": {
    "allow": [
      "Bash(bash .claude/flow/flow_init.sh)",
      "Bash(bash .claude/flow/run_tests.sh:*)",
      "Bash(bash .claude/flow/finish.sh)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      { "matcher": ".*", "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/guard.py\" main" } ] }
    ],
    "SubagentStop": [
      { "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/capture_report.py\"" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/stop_guard.py\"" } ] }
    ]
  }
}
```

注意：`guard.py main` 會套用在該專案**所有** Claude Code 對話，主對話只能讀規格與流程檔、只能執行 `.claude/flow/*.sh`。
平常開發不跑流程時，可在 `.claude/settings.local.json` 放 `{ "disableAllHooks": true }` 暫時關閉，**跑流程前務必刪掉**，否則隔離無效。

### 3. 設定 `flow.config.json`

通常由 `/spec-draft` 依技術棧自動填寫，人只需在確認規格時看一下套件白名單。欄位說明：

| 欄位 | 說明 |
|---|---|
| `max_rounds` | 最多幾輪修正 |
| `coder_can_read_tests` | coder 是否可讀測試（預設 false，維持隔離） |
| `on_fail_update` | 測試失敗時更新哪份提示；`coder_only` 只改 coder.md |
| `parallel_coder_tester` | true：coder 與 tester 同時跑；false：先 tester 再 coder |
| `spec_dir` | 規格目錄，內含 `architecture.md`、`rules.md` |
| `src_dirs` | coder 唯一可寫的目錄或檔案（可多個）。結尾 `/` 為目錄，沒有 `/` 為單一檔案（例如 `frontend/package.json`）。不可設為專案根目錄 |
| `test_dirs` | test-designer 唯一可寫的目錄或檔案（可多個）。測試設定檔（例如 `frontend/vitest.config.ts`）放這裡，coder 才無法用設定排除測試 |
| `test_framework` | 給 test-designer 的框架說明文字 |
| `setup_command` | 選填。⑥ 在白名單檢查通過後、測試前執行，用來安裝套件；exit code 非 0 即該輪失敗 |
| `test_command` | ⑥ 在專案根目錄以 `bash -c` 執行；exit code 0 為通過 |
| `no_tests_regex` | 選填。log 符合此正規式時視為「沒有測試」並判失敗（防止 0 個測試也算通過）；空字串表示不檢查 |
| `deps_check` | 選填。套件白名單：`[{"type": "pip"\|"npm", "file": "<套件檔>", "allow": [...]}]`。⑥ 安裝前由腳本檢查，宣告了白名單外的套件（requirements.txt 的 `-r`、`-e` 等選項也算）就不安裝、該輪失敗 |

常見設定範例：

```jsonc
// Python + pytest
"src_dirs": ["src/"], "test_dirs": ["tests/"], "test_framework": "pytest",
"test_command": "python3 -m pytest -v", "no_tests_regex": "no tests ran"

// Node + Jest
"src_dirs": ["src/"], "test_dirs": ["__tests__/"], "test_framework": "Jest",
"test_command": "npx jest --ci", "no_tests_regex": "No tests found"

// React + FastAPI（前後端分離，完整範例見 examples/react-fastapi/）
"src_dirs": ["backend/app/", "backend/requirements.txt", "frontend/src/", "frontend/package.json", "frontend/vite.config.ts", "frontend/tsconfig.json", "frontend/index.html"],
"test_dirs": ["backend/tests/", "frontend/tests/", "frontend/vitest.config.ts"],
"setup_command": "cd backend && python3 -m pip install -q -r requirements.txt && cd ../frontend && npm install --silent --no-audit --no-fund",
"test_command": "cd backend && python3 -m pytest tests -v && cd ../frontend && npx vitest run",
"no_tests_regex": "no tests ran|No test files found"

// Go（測試檔與程式同目錄的語言，建議把測試放在獨立的 package 目錄，例如 internal/foo_test/，才能隔離讀寫）
"src_dirs": ["internal/foo/"], "test_dirs": ["internal/foo_test/"], "test_framework": "Go testing",
"test_command": "go test ./... -v", "no_tests_regex": "no test files"
```

### 4. 寫規格

執行 `/spec-draft`，從系統描述（Design Patterns、SOLID）、邊界（System Boundaries）、業務規則（Business Rules）三個角度描述需求（也可以直接手寫 `spec/` 的三份檔案與 `flow.config.json`，格式參考 `examples/react-fastapi/`、`examples/discount/`）。

### 5. 建議加入目標專案的 `.gitignore`

```
.flow/
.claude/settings.local.json
node_modules/
```

## 執行

```text
1. /spec-draft 我要做一個……          ← 用 pattern／SOLID／邊界／業務規則描述，回答設計與業務反問，確認草稿
2. ! bash .claude/flow/approve_spec.sh   ← 人自己執行（終端機執行也可以）
3. /senior-flow                           ← 或用下面的非互動指令
```

```bash
claude -p "/senior-flow" --permission-mode acceptEdits --allowedTools "Bash(bash .claude/flow/flow_init.sh)" "Bash(bash .claude/flow/run_tests.sh:*)" "Bash(bash .claude/flow/finish.sh)"
```

資料夾未信任時，`settings.json` 的 `permissions.allow` 會被忽略，所以允許清單用命令列傳入。

結束狀態（`.flow/state.json` 的 `status`）：
- `done`：最後一輪測試通過，且一致性報告總結為「一致」
- `needs_review`：測試失敗或報告不一致（已達 `max_rounds`），需要人特別檢查

人只看 `.flow/report.md`：第 0 節摘要、A／B／R／E 對照表，以及第 6 節「規格本身的問題」（下次修改規格的依據）。
不符合需求時，修改 `spec/` 的三份檔案（或再用 `/spec-draft`），重新確認後重跑 `/senior-flow`。

## 範例

### 折扣計算（Python）

`examples/discount/` 是跑通過的玩具題目（Python unittest）。在本 repo 試跑：

```bash
cp examples/discount/architecture.md examples/discount/boundaries.md examples/discount/rules.md spec/
cp examples/discount/flow.config.json .
bash .claude/flow/approve_spec.sh
```

### 折扣計算 API + 表單（React + FastAPI）

`examples/react-fastapi/` 示範前後端分離：Strategy（折扣規則）、OCP、DIP（router → service、元件 → props 注入）、API 合約，以及由 agent 產生 `package.json`、`requirements.txt` 等設定檔與套件白名單。需要 Python 3.10+、Node.js 18+ 與網路（安裝套件）。

```bash
cp examples/react-fastapi/architecture.md examples/react-fastapi/boundaries.md examples/react-fastapi/rules.md spec/
cp examples/react-fastapi/flow.config.json .
bash .claude/flow/approve_spec.sh
```

## 已知限制

- 資料夾未信任時，subagent frontmatter 裡的 hook 不執行；隔離靠 `settings.json` 層的 `guard.py`。
- Claude Code 不讓 subagent 寫報告檔，所以 ⑦ 改為以最終回覆輸出。
- 每次 `/senior-flow` 會清掉 `.flow/`；程式與測試目錄不清，重跑前視需要手動清除。
- 隔離是以目錄為單位；測試和程式放在同一目錄的專案，需要先調整成分開的目錄。
- `setup_command`、`test_command` 由腳本直接執行；由 `/spec-draft` 產生時，確認規格前請看過這兩個指令。
- 套件白名單只檢查套件名稱，不檢查版本；白名單內的套件安裝時仍可能執行其安裝腳本，白名單請只列信任的套件。
- 架構約束（A*）中「審查」類由一致性 Agent 判定，屬於 AI 判斷；需要硬性保證的約束請標為「測試」。
