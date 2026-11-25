# LLM 使用規範（LiteLLM）

## 唯一出口

- 所有 LLM 呼叫只經 `app/services/llm/gateway.py`
- 禁止在其他地方 import `litellm`、`openai`、`anthropic` 等 SDK；唯一例外是 `services/llm/chatgpt_auth.py` 可 import `litellm.llms.chatgpt`，只用於 ChatGPT 訂閱登入（見 [ADR 0006](../adr/0006-llm-config-settings.md)）
- 模型名稱不寫死在程式，由使用者設定：DB 分開存 `provider` 與 `model`，由 `services/llm/providers.py` 組成 LiteLLM 格式 `prefix/model`
- LiteLLM 在 import 時會下載模型價格表；`services/llm/__init__.py` 設定 `LITELLM_LOCAL_MODEL_COST_MAP=True` 改用內建價格表（內網）

## 模型設定（網頁 `/settings/llm`）

- 欄位：名稱（不可重複）、服務類型、模型名稱（不含前綴）、`api_base`、API key、timeout
- 服務類型與欄位規則：

  | provider | 畫面名稱 | LiteLLM 前綴 | API 金鑰 | API 位址 |
  |---|---|---|---|---|
  | `openai` | Codex・API 金鑰 | `openai/` | 必填 | 不使用 |
  | `chatgpt` | Codex・ChatGPT 訂閱 | `chatgpt/responses/`（Codex 後端只接受 Responses API；LiteLLM 只對內建清單上的模型自動改走 Responses，新模型需明確指定） | 不使用（登入 token） | 不使用 |
  | `gemini` | Gemini | `gemini/` | 必填 | 不使用 |
  | `ollama` | 本地・Ollama | `ollama_chat/` | 不使用 | 選填（預設 `http://localhost:11434`） |
  | `openai_compatible` | 本地・OpenAI 相容 | `openai/` | 選填 | 必填 |

  前端 `lib/llmProviders.ts` 的欄位規則須與 `services/llm/providers.py` 一致
- 畫面上 Ollama 與 OpenAI 相容合併為一個選項「本地模型」：使用者只填伺服器位址（可留空＝Ollama 預設位址），後端依序試 `/api/tags`（Ollama）、`/v1/models`（OpenAI 相容，只填主機時自動補 `/v1`），以第一個成功的判斷類型；儲存時仍為 `ollama`／`openai_compatible`
- 新增與編輯都用逐步工作表：選擇服務類型 → 連線設定 → 選擇模型 → 命名與確認
- 「查詢可用模型」API（模型下拉選單），不讓使用者自己猜模型名稱：
  - `POST /api/v1/available-models`：Codex（`GET /v1/models`）、Gemini（`GET /v1beta/models`，只留 `generateContent`）、ChatGPT 訂閱（與 Codex CLI 相同，以登入 token 呼叫 `GET https://chatgpt.com/backend-api/codex/models?client_version=…`，只留 `visibility=list`、依 `priority` 排序，即此帳號在 Codex 模型選單看得到的模型；版本號由 `services/llm/codex_version.py` 決定：`CHATGPT_CLIENT_VERSION` 有設定就固定使用，否則自動查詢 npm `@openai/codex` 最新版本並快取，失敗時用 `CHATGPT_CLIENT_VERSION_FALLBACK`）
  - `POST /api/v1/available-models/local`：偵測本地伺服器類型並回傳實際位址
  - Codex、Gemini 只列可對話的模型：以 LiteLLM 價格表的 `mode`（`chat`／`responses`）判斷，未收錄的新模型以名稱排除 embedding、語音、影像等
  - 以 httpx 直接查詢（`services/llm/model_catalog.py`），不用 LiteLLM 的 `get_valid_models`：後者為同步呼叫、失敗一律回空清單，Ollama 失敗時甚至回傳內建清單
  - 金鑰放在 body（不放 URL）；編輯時可只帶 `config_id` 沿用已儲存的金鑰，但只限同一服務（本地模型的兩種伺服器可互用）
  - 清單取不到時顯示原因並可改為手動輸入模型名稱
- 換了服務類型卻沒給新金鑰時，後端清除舊金鑰（舊金鑰屬於另一個服務）
- 可儲存多組；同一時間只有一組「使用中」（`is_active`，由 DB 部分唯一索引保證），gateway 呼叫時讀取使用中的設定
  - 第一筆自動設為使用中；新增、編輯不改變使用中；使用中的設定不可刪除
- ChatGPT 訂閱：以 OAuth 裝置碼登入（網頁顯示驗證碼），token 存 `CHATGPT_TOKEN_DIR`（預設 `backend/data/chatgpt/`，不進版控）；呼叫前先確認 token 可用，失敗回「請重新登入」
- 「測試對話」API：`POST /api/v1/llm-configs/{id}/chat`，SSE 串流 `delta`／`done`／`error` 事件
  - 對話歷史只存在前端；後端不保存、不寫 log
  - 不帶 `temperature`（部分 Codex 模型只接受預設值）；`drop_params=True`；重試次數取 `LLM_CHAT_NUM_RETRIES`（預設 0，錯誤立即顯示）
  - 錯誤轉成繁中可操作訊息（金鑰無效、找不到模型、無法連線、逾時、額度上限），不回傳原始例外字串；訊息與比對邏輯在 `services/llm/error_messages.py`，LiteLLM 例外類別的對照表留在 gateway 傳入（該模組不 import litellm）
  - 串流轉送在 `services/llm/chat_stream.py`（不 import litellm）；請求結束時（含用戶端斷線、回應開始前取消）由 endpoint 的 dependency 呼叫 `ChatStream.aclose()` 關閉上游，不依賴垃圾回收
- 設定變更寫入 `setting_change_logs`（只記欄位名稱，不含 key 值）

## 共用 System Prompt（網頁 `/settings/llm`）

詳見 [ADR 0007](../adr/0007-llm-system-prompt.md)。

- 所有呼叫（測試對話、日後稽核）都先帶上這段指示，放在最前面的 `system` 訊息；稽核時接在規則 prompt 之前；內容為空表示不使用
- 版本化：`llm_system_prompts` 只新增、不修改，每次儲存新增一個 `version`；內容相同時不新增版本；清空後不送 system 訊息，但仍記錄該版本號
- API：`GET /api/v1/llm-system-prompts/current`、`POST /api/v1/llm-system-prompts`；上限 `LLM_SYSTEM_PROMPT_MAX_CHARS`
- 儲存時帶 `base_version`（開始編輯時的版本）；已有較新版本時回 409，不覆寫；內容相同時不算衝突
- 測試對話的 `done` 事件附 `system_prompt_version`；log 與變更紀錄只記版本號，不記內容
- ChatGPT 訂閱只送共用 system prompt，不帶 LiteLLM 內建的 Codex CLI 指示：
  - gateway 在呼叫前把環境變數 `CHATGPT_DEFAULT_INSTRUCTIONS` 設為共用 system prompt
  - 共用 system prompt 為空時移除這個環境變數，改回 Codex 內建指示（Codex 後端需要 instructions）
  - 這個環境變數只能由 gateway 設定

## API key 安全

- 以 Fernet（`cryptography`）加密存 DB，加密金鑰來自環境變數 `LLM_KEY_ENCRYPTION_KEY`；更換加密金鑰後已存的 key 無法解密，需重新輸入
- 只在呼叫模型服務的當下解密（gateway 的對話、`model_listing` 的清單查詢），不存入任何全域變數或快取
- 遮罩值（如 `sk-…abcd`）在儲存時另存於 `api_key_hint`；API 回傳前端只給遮罩值，前端永遠拿不到明文；編輯時留空表示沿用
- 不得出現在 log、例外訊息、稽核結果中；不開啟 LiteLLM 的 verbose／debug log

## gateway 介面（結構化輸出）

實作位於 `services/llm/structured.py`，由 `services/llm/gateway.py` 重新匯出。呼叫端只能從 `gateway` 匯入。

```python
async def complete_structured[T: BaseModel](
    session: AsyncSession,         # 只讀取使用中設定與共用 system prompt；讀完即結束交易
    request: LLMRequest,           # rule_code、prompt_name、prompt_version、variables（皆為字串）
    output_schema: type[T],        # 通常是 RuleOutput 的子類別
) -> LLMResult[T]:                 # parsed、model、prompt_version、system_prompt_version、
                                   # prompt_tokens、completion_tokens、cost_usd、duration_ms、input_digest、attempts
```

例外：

| 例外 | HTTP | 說明 | 稽核的處理 |
|---|---|---|---|
| `LLMNotConfiguredError` | 409 | 沒有使用中的模型設定 | 不寫入紀錄，回 409 |
| `LLMOutputError` | 502 | 格式重試後仍不符合 `output_schema` | `COMPLETED`＋`NEEDS_REVIEW`，不可視為 `PASS` |
| `LLMConnectionError` | 502 | 連線、驗證、額度等錯誤（LiteLLM 例外轉換，訊息不含金鑰） | `FAILED` |

執行步驟：

1. 讀取使用中的模型設定（`crud/llm_config.get_active`）與共用 system prompt 快照（`read_call_snapshot`）。讀完即結束交易，呼叫期間不占 DB 連線。
2. ChatGPT 訂閱：呼叫前確認 token 可用（`ensure_access_token`）。
3. 組呼叫參數（`call_support.prepare_call`）：`timeout` 取自該設定的逾時秒數、`drop_params=True`、`temperature=0`、`num_retries` 取 `LLM_STRUCTURED_NUM_RETRIES`、`max_tokens` 取 `LLM_MAX_OUTPUT_TOKENS`（預設 4096；Ollama 由 LiteLLM 轉成 `num_predict`，ChatGPT 訂閱不接受此參數而被略過）。
4. 渲染規則 prompt（`prompt_loader.render_prompt`，`StrictUndefined`，缺變數直接失敗）。`input_digest` 為渲染後 prompt 的 sha256，不存全文。
5. 訊息順序：共用 system prompt（有設定時）→ 規則 prompt。
6. 非串流呼叫 `litellm.acompletion`，帶 `response_format={"type": "json_object"}`，受 `LLM_MAX_CONCURRENCY` 限制。
7. 以 `output_schema.model_validate_json` 驗證（先去除外層的 ```` ```json ```` 圍欄）。不符時把錯誤位置與錯誤類型（不含輸入值）附在對話中重試，最多 `LLM_MAX_RETRIES` 次。回應的 `finish_reason` 為 `length`（達輸出上限被截斷）時不做格式重試，直接以 `LLMOutputError`「模型輸出超過長度上限而被截斷…」結束：同一模型、同一輸入重試多半再被截斷，只會拖到逾時（2026-11-25 Ollama 模型單次輸出逾 4,800 tokens 未停的事件）。log 只記截斷時的輸出 token 數，不記內容。
8. 仍不符 → 拋出 `LLMOutputError`。
9. 記錄 model、prompt_version、system_prompt_version、token 用量、成本（`litellm.completion_cost`，查不到時為 `None`，不影響結果）、耗時、attempts。

重試的關係：

- 格式重試（第 7 步）與網路重試（LiteLLM `num_retries`，網路錯誤、429、逾時，指數退避）分開計算。
- 最多呼叫次數為 (1 + `LLM_MAX_RETRIES`) × (1 + `LLM_STRUCTURED_NUM_RETRIES`)，預設為 9 次。

併發與 ChatGPT 訂閱：

- 併發閘門 `_GATE` 是程序內的 `asyncio.Semaphore`，上限 `LLM_MAX_CONCURRENCY`；每個 event loop 各自建立。閘門只涵蓋模型呼叫，不涵蓋 DB。
- ChatGPT 訂閱的 `CHATGPT_DEFAULT_INSTRUCTIONS` 只能在 `CHATGPT_INSTRUCTIONS_LOCK` 內設定，並且只在 `acompletion` 回傳後才解除鎖。與測試對話共用同一把鎖（見 [ADR 0007](../adr/0007-llm-system-prompt.md)）。
- 去識別化的插入點是 `structured.py` 的 `_preprocess`（見 [ADR 0002](../adr/0002-llm-phi-policy.md)），目前原樣傳遞、不做任何處理。接入真實病患資料前必須在這裡補上去識別化，並更新本節。

## Prompt 規範

- 位置：`app/prompts/<prompt_name>/v<N>.j2`（Jinja2），內容繁中。`prompt_name` 與規則的 `prompt_name` 相同，例如 `r03_admission_completeness`，只允許小寫英數與底線（`LLMRequest` 驗證）。現有：`r01_admission_course`、`r02_copy_paste`、`r03_admission_completeness`、`r04_assessment_followup`、`r05_transfer_summary`、`r06_consultation`、`r07_medication_followup`
- 渲染：`prompt_loader.py`，`StrictUndefined`（缺變數直接失敗）、不做 autoescape（純文字）
- 版本：已用於產出稽核結果的 prompt 不得就地修改語意，改版請新增 `v<N+1>.j2`；稽核結果記錄 `prompt_version`，確保可重現
- 必要要素清單與院方欄位對照由程式常數注入，不在 prompt 內重複寫死
- 資料區塊格式：每筆紀錄以 `<record source="…" id="…" date="…" time="…">` 標示，欄位為「標籤：值」；多行值以縮排續行（見 `services/audit/records.py`）
- 結構：

```
[角色] 你是護理紀錄稽核助理，只做紀錄一致性與完整性檢查，不做臨床判斷。
[任務] 本規則要檢查什麼。
[判斷準則] 必要要素（由程式注入）、何種情況屬於不一致。
[輸入資料] 每筆資料以標籤標示來源與 record_id，例：
  <record source="nursing_progress_note" id="…" date="…">…</record>
[輸出格式] JSON，符合 output_schema。
[限制]
  - 只根據提供的資料判斷，不得推測或補完
  - 每個結論必須引用原文片段（excerpt）與 record_id
  - 資料不足以判斷時回傳 NEEDS_REVIEW
```

## Hallucination guard（Evidence 核對）

實作：`services/audit/evidence.py`、`services/audit/text.py`。完整規則見 [audit-rules.md](audit-rules.md#evidence-核對)。

- LLM 只回傳 `record_id` 與 `excerpt`；來源、欄位、日期、時間由程式依 `record_id` 回填
- 比對前去除**所有空白**與格式字元、私用區字元、變體選擇器（`squash`），不是只摺疊空白
- `excerpt` 必須是該紀錄某欄位值（或「標籤：值」「標籤值」）的子字串；跨欄位的片段則比對整筆原文與時間字串
- 驗證失敗的 Evidence 丟棄；`WARNING` 的 finding 若無任何有效 Evidence，降為 `NEEDS_REVIEW`
- 整體判定取 LLM 整體判定與各 finding 中較嚴重者；`WARNING` 整體若無有效 Evidence 同樣降為 `NEEDS_REVIEW`

## 測試與評估

- 單元測試一律 mock gateway，不打真實 API（`tests/services/llm/test_structured.py`、`tests/services/audit/`）
- 準確率評估與單元測試分開：規劃中的 `backend/evaluation/` 以護理長標註的 golden set 計算各規則 precision／recall／F1，手動執行（會產生費用）。**目前尚未建立。**
