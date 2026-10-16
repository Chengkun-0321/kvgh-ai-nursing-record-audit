# ADR 0012：採用規格驅動的多代理開發流程，並依本專案調整

- 狀態：提議
- 日期：2026-10-17

## 背景

- 從上游（學長方法）引入一套流程：
  - 人負責寫規格（A／B／R／E）
  - coder 與 test-designer 在讀寫隔離下各自撰寫程式與測試
  - 腳本跑測試，一致性 Agent 產出報告給人審
- 原樣套用到本專案時有以下阻礙（2026-10-17 實測）：
  1. guard 對主對話**永遠**只允許執行 `.claude/flow/*.sh`、只能讀 spec。平常開發必須用 `disableAllHooks` 關掉 hooks，連帶讓隔離失效。
  2. 流程角色讀不到 CLAUDE.md 與 `docs/conventions/`，專案的 MUST／NEVER 不會被遵守。
  3. `flow.config.json` 是範例專案的設定。README 範例用系統 `python3 -m pip` 安裝，違反「不可全域安裝」。
  4. `requirements-dev.txt` 首行的 `-r requirements.txt` 一律被白名單檢查判為違規。
  5. 前端測試與程式放在同一個目錄，guard 以目錄為單位，無法隔離。
  6. 流程的業務規則編號 `R1` 和稽核項目代碼 `R01`～`R11` 撞名。

## 決策

1. **guard 只在流程執行中限制主對話**。以 `.flow/state.json` 的 `status == running` 判斷。
   - 流程角色一律受限。
   - `approve_spec.sh`、`.approved` 不論何時都禁止 AI 操作。Bash 依指令結構判斷，唯讀操作不擋。
   - hooks 常駐開啟。
2. **專案規範以唯讀參考文件提供**。
   - 新增 `reference_paths`（所有角色可讀）、`coder_read_paths`、`tester_read_paths`。
   - 關鍵約束寫成 `spec/architecture.md` 的固定條目 A1～A7，其中 A1～A3 每次都有架構測試。
   - 新增 `state.py check_config`，檢查讀寫範圍會不會讓 coder 讀到測試、讓 test-designer 讀到程式，或讓可寫範圍碰到規格、`flow.config.json`、`.claude/` 等流程控制檔。
   - CLAUDE.md「核心原則」與 MUST／NEVER 優先於 spec，一致性報告逐條判定。
3. **`flow.config.json` 改為本專案預設**。
   - 安裝與測試只用 `backend/.venv` 和專案內的 npm。
   - `test_command` 涵蓋 pytest、ruff、mypy、vitest、eslint、tsc。
   - lint／型別設定檔、`alembic/`、`requirements-dev.txt` 不列入任何可寫範圍。
4. **前端測試由 `frontend/src/**/*.test.ts` 搬到 `frontend/tests/`**，以 `@/` 匯入被測模組。
5. **業務規則編號改為 `BR*`**，`A*`／`B*`／`E*` 不變；`examples/` 維持上游原樣。

## 影響

- **好處**：平常開發與流程可以共存，不必切換 hooks；流程產出受專案規範與 DoD 檢查約束。
- **代價**：
  - 與上游流程有差異，日後同步上游時要逐項比對（差異列在 [spec-flow.md](../conventions/spec-flow.md)）。
  - Bash 的確認檢查只防誤操作，不是安全邊界。
  - 每輪都會跑完整 lint 與型別檢查，耗時較長。
- **後續**：
  - 第一次用流程開發功能時，就是端到端試跑，要確認 prompt-builder／coder 有讀 `reference_paths`。
  - 跑完後依報告第 6 節修正 spec 範本。
