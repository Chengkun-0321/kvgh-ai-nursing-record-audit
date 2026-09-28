# ADR 0007：共用 System Prompt（版本化、套用所有呼叫、ChatGPT 訂閱不帶 Codex 內建指示）

- 狀態：提議
- 日期：2026-09-28

## 背景

- 以 ChatGPT 訂閱測試對話時，模型自稱「GPT-5／Codex CLI」，並以簡體中文回答。
- 原因是 LiteLLM 每次都在 Responses API 的 `instructions`（等同 system prompt）最前面加上 Codex CLI 的內建指示（`litellm/llms/chatgpt/common_utils.py` 的 `CHATGPT_DEFAULT_INSTRUCTIONS`，約 7,500 字元）。那段指示全是寫程式的規則，對稽核沒有幫助：
  - 可能與稽核要求的「只輸出 JSON、只依紀錄判斷」衝突。
  - 每次呼叫多送約 1,600 個 tokens。
- 使用者希望在設定頁統一設定一段 system prompt，所有模型都套用。

## 決策

1. **一段共用 system prompt，套用到所有呼叫**：
   - 所有模型設定、測試對話與日後的稽核呼叫都會先帶上這段指示，放在最前面的 `system` 訊息。
   - 稽核時接在規則 prompt 之前。
   - 內容為空表示不使用。
2. **版本化**：
   - 資料表 `llm_system_prompts` 只新增、不修改，每次儲存新增一個 `version`（遞增、唯一），最新的一筆為目前使用的版本。
   - 內容相同時不新增版本；清空也是一個新版本，呼叫時不送 system 訊息，但仍記錄該版本號，才能分辨「當時已清空」與「從未設定」（從未儲存過才是 null）。
   - 測試對話的 `done` 事件回傳 `system_prompt_version`；日後 `LLMResult` 與稽核結果也要記錄這個版本號，確保可重現。
   - log 與設定變更紀錄只記版本號與欄位名稱，不記內容。
3. **ChatGPT 訂閱只送共用 system prompt**：
   - LiteLLM 從環境變數 `CHATGPT_DEFAULT_INSTRUCTIONS` 讀取要放在最前面的基底指示，而且基底已包含在 `instructions` 內時不重複加入。
   - gateway 在呼叫 `chatgpt/` 模型前，把這個環境變數設為共用 system prompt，並送出相同內容的 system 訊息，最後送出的 `instructions` 就只有共用 system prompt。
   - 共用 system prompt 為空時，移除這個環境變數，改回 Codex 內建指示，因為 Codex 後端需要有 instructions。
   - 2026-09-28 實測 gpt-6-luna：
     - Codex 後端接受自訂的 instructions。
     - 回覆為繁體中文。
     - 輸入由 1,631 tokens 降為 19 tokens。
4. **API**：
   - `GET /api/v1/llm-system-prompts/current`
   - `POST /api/v1/llm-system-prompts`（新增一個版本）
   - 字數上限 `LLM_SYSTEM_PROMPT_MAX_CHARS`（8,000）。
5. **不覆寫較新的版本**：
   - 儲存時必須帶 `base_version`（開始編輯時的版本，從未儲存過為 null）。
   - 最新版本已不是 `base_version` 時回 409，請使用者先複製內容、重新整理後再儲存；前端保留草稿。
   - 內容與最新版本相同時不算衝突，直接回傳目前版本。
   - 兩個請求以同一個 `base_version` 同時儲存時，由 `version` 唯一約束擋下後到者，同樣回 409。

## 影響

- **好處**：
  - 所有模型的回答語言與角色一致，可在設定頁直接調整，並立即以測試對話確認。
  - ChatGPT 訂閱每次呼叫省下約 1,600 個 tokens。
- **代價與風險**：
  - 修改共用 system prompt 會改變之後所有稽核的輸出，所以稽核結果必須記錄版本號，並在設定頁提示這一點。
  - ChatGPT 的做法依賴 LiteLLM 的內部行為（環境變數名稱、不重複加入的判斷）。`tests/services/llm/test_gateway.py` 會攔下 LiteLLM 實際組出的請求，確認 `instructions` 只有共用 system prompt；升級 LiteLLM 時，這支測試能提早發現行為變了。
  - 這個環境變數是整個程序共用的狀態，只由 gateway 設定。如果兩個呼叫之間剛好儲存了新版本，可能用到較新的內容；影響僅限該次回覆。
- **後續**：實作 `complete_structured` 時，要讓共用 system prompt 接在規則 prompt 之前，並記錄 `system_prompt_version`。
