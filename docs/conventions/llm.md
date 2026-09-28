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
  - `POST /api/v1/available-models`：Codex（`GET /v1/models`）、Gemini（`GET /v1beta/models`，只留 `generateContent`）、ChatGPT 訂閱（與 Codex CLI 相同，以登入 token 呼叫 `GET https://chatgpt.com/backend-api/codex/models?client_version=…`，只留 `visibility=list`、依 `priority` 排序，即此帳號在 Codex 模型選單看得到的模型；版本號為 `Settings.CHATGPT_CLIENT_VERSION`）
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
  - 錯誤轉成繁中可操作訊息（金鑰無效、找不到模型、無法連線、逾時、額度上限），不回傳原始例外字串
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

## gateway 介面

```python
async def complete_structured(
    request: LLMRequest,           # rule_code、prompt 名稱與版本、模板變數
    output_schema: type[T],        # 期望輸出的 Pydantic model
) -> LLMResult[T]:                 # parsed、model、prompt_version、system_prompt_version、token 用量、成本、耗時
```

執行步驟：

1. 讀取啟用中的模型設定並解密 key
2. 組成訊息：共用 system prompt（有設定時）→ 以 `prompt_loader` 渲染的規則 prompt
3. `preprocess` hook（目前 pass-through；未來接真實資料時插入去識別化，見 [ADR 0002](../adr/0002-llm-phi-policy.md)）
4. `litellm.acompletion(...)`：`temperature=0`、`timeout` 取自設定；模型支援時使用 `response_format` 要求 JSON
5. 以 `output_schema` 驗證輸出；失敗時附上驗證錯誤重試，最多 `LLM_MAX_RETRIES` 次
6. 仍失敗 → 拋出 `LLMOutputError`，規則轉為 `NEEDS_REVIEW`，**絕不靜默視為 PASS**
7. 記錄 model、prompt_version、system_prompt_version、token 用量、成本（`litellm.completion_cost`）、耗時

網路錯誤、429、timeout 以指數退避重試（LiteLLM `num_retries`），與第 5 步的格式重試分開計算。

## Prompt 規範

- 位置：`app/prompts/<rule_code>_<name>/v<N>.j2`（Jinja2），內容繁中
- 版本：已用於產出稽核結果的 prompt 不得就地修改語意，改版請新增 `v<N+1>.j2`；稽核結果記錄 `prompt_version`，確保可重現
- 必要要素清單由程式常數注入，不在 prompt 內重複寫死
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

## Hallucination guard

- LLM 回傳的每筆 Evidence，後端須驗證 `excerpt` 確實存在於對應 `record_id` 的原文（正規化空白後比對）
- 驗證失敗的 Evidence 丟棄；若無任何有效 Evidence，結果降為 `NEEDS_REVIEW`

## 測試與評估

- 單元測試一律 mock gateway，不打真實 API
- 準確率評估與單元測試分開：`backend/evaluation/` 以護理長標註的 golden set 計算各規則 precision／recall／F1，手動執行（會產生費用）
