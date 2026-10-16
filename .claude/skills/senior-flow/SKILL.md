---
name: senior-flow
description: 執行學長修訂版流程（人只寫規格、看報告）：③ Prompt Builder → ④ coder／⑤ test-designer → ⑥ 跑測試 → ⑦ 一致性 Agent，在 ⑧ 人審前停下。
disable-model-invocation: true
---
你是流程指揮。你不寫程式、不寫測試、不讀程式與測試目錄（`flow.config.json` 的 `src_dirs`、`test_dirs`），只依序呼叫角色和腳本。先讀 `flow.config.json` 取得 `max_rounds` 和 `parallel_coder_tester`。

傳給 subagent 的訊息只能是下列指定的指示，不得轉述測試內容、程式碼或測試紀錄。

腳本一律在專案根目錄單獨執行，寫法就是 `bash .claude/flow/<名稱>.sh [輪次]`，不加 `cd`、`&&` 或其他指令。

## 步驟

1. 執行 `bash .claude/flow/flow_init.sh`。
   如果輸出「無法開始」（spec 不存在、未經人確認，或確認後被修改），把訊息原文交給人後**立即結束**，不要嘗試修改 spec 或自行確認。
   成功時令 N = 1。

2. **第 N 輪**
   a. 呼叫 subagent `prompt-builder`：
      - N = 1：「第 1 輪：依 spec/ 產生 .flow/prompts/coder.md 和 .flow/prompts/tester.md。」
      - 因測試失敗而進入第 N 輪：「第 N 輪修正，原因：測試失敗，紀錄在 .flow/runs/round-(N-1).log。」
      - 因一致性不符而進入第 N 輪：「第 N 輪修正，原因：一致性不符，見 .flow/report.md。」
   b. 決定要跑的角色：N = 1 時是 coder 和 test-designer；N > 1 時讀 `.flow/prompts/next.json` 的 `rerun`。
      兩個都要跑時：`parallel_coder_tester` 為 true 就在**同一則訊息**同時呼叫兩個 subagent；為 false 就先呼叫 test-designer，完成後再呼叫 coder。訊息內容：
      - coder：「依 .flow/prompts/coder.md 實作，第 N 輪。」
      - test-designer：「依 .flow/prompts/tester.md 撰寫測試，第 N 輪。」
   c. ⑥ 執行 `bash .claude/flow/run_tests.sh N`（腳本依序做套件白名單檢查、安裝、測試，不經 AI）。
   d. 失敗：N < max_rounds 時 N = N + 1，回到 2a（原因：測試失敗）；N = max_rounds 時進入步驟 3。
      通過：進入步驟 3。

3. **⑦** 呼叫 subagent `consistency-checker`：「產生第 N 輪的一致性報告。」
   它的最終回覆會由 hook 自動存成 `.flow/report.md`，你不要自己存檔或轉寫。
   讀 `.flow/report.md` 的最後一行：
   - `總結：一致`，或已達 max_rounds：進入步驟 4。
   - `總結：不一致…` 且 N < max_rounds：N = N + 1，回到 2a（原因：一致性不符）。

4. 執行 `bash .claude/flow/finish.sh`。如果它回報無法結束，依訊息補做缺少的步驟。

5. **停在 ⑧**：把以下內容交給人，然後結束。不要自己判斷是否符合需求。人不看程式碼，只看這份交付內容與報告。
   - finish.sh 的輸出（狀態、輪數）。`done` 表示測試通過且報告一致；`needs_review` 表示測試失敗或報告不一致，需要人特別檢查
   - 每一輪的測試結果（通過／失敗；失敗時註明是套件白名單、安裝或測試哪一段）
   - `.flow/report.md` 第 0 節「摘要」原文
   - 報告中判定為「不一致」「未覆蓋」的編號（A／B／BR／E）
   - 報告第 6 節「規格本身的問題」原文
   - 提醒：完整報告在 `.flow/report.md`。不符合需求時，人只需要修改規格目錄下的 architecture.md、boundaries.md、rules.md（或用 /spec-draft 修改），重新確認後重跑 /senior-flow
   - ⑨ 收尾清單（本專案；流程結束後 status 已不是 running，主對話不再受 guard 限制，由人決定何時做）：
     1. 有 model 變更：在 `backend/` 執行 `alembic revision --autogenerate -m "繁中描述"`，人工檢查產出後 `alembic upgrade head`（流程角色不能寫 `alembic/`）
     2. 同步 `docs/glossary.md`、ADR、`docs/conventions/audit-rules.md`（新詞彙、新決策、規則清單狀態）
     3. 檢查 `frontend/package-lock.json` 的 diff（安裝會改寫 lock；套件有變動才 commit）
     4. 與 Codex 互審本次 diff
     5. 跑完整 Definition of Done 檢查（見 CLAUDE.md）
     6. 使用者要求時才 commit；`spec/` 與 `spec/.approved` 和程式放同一個 commit
