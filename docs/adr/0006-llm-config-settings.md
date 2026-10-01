# ADR 0006：LLM 模型設定頁（多組設定、服務類型、ChatGPT 訂閱登入、串流測試對話）

- 狀態：提議
- 日期：2026-09-28

## 背景

使用者要在網頁上設定 LiteLLM 串接的模型，需求如下：

- 支援 Codex、Gemini 與本地模型。
- 可儲存多組設定，自行選擇目前使用哪一組。新增一組不會刪除或停用舊的。
- 設定寫入後端，重新開啟頁面不會還原。
- 頁面內可直接輸入對話測試，並即時看到回應。

其中 Codex 要支援兩種方式：OpenAI API key，以及 ChatGPT Plus／Pro 訂閱登入。本地模型則要同時支援 Ollama 與 OpenAI 相容伺服器（LM Studio、vLLM、llama.cpp）。

## 決策

1. **服務類型（`LlmProvider`）**：DB 分開存 `provider` 與 `model`，由 `services/llm/providers.py` 組成 LiteLLM 的 `prefix/model`。

   | provider | LiteLLM 前綴 | API 金鑰 | API 位址 |
   |---|---|---|---|
   | `openai`（Codex・API 金鑰） | `openai/` | 必填 | 不使用 |
   | `chatgpt`（Codex・ChatGPT 訂閱） | `chatgpt/responses/` | 不使用（改用登入 token） | 不使用 |
   | `gemini` | `gemini/` | 必填 | 不使用 |
   | `ollama`（本地） | `ollama_chat/` | 不使用 | 選填，預設 `http://localhost:11434` |
   | `openai_compatible`（本地） | `openai/` | 選填（未填時送固定占位值） | 必填 |

   切換服務類型時，後端清掉新類型用不到的欄位（例如切到 `chatgpt` 會移除已存的金鑰）。
2. **多組設定、單一使用中**：
   - `llm_configs.is_active` 同一時間最多一筆，由部分唯一索引 `uq_llm_configs_is_active`（只索引 `is_active = true` 的列，SQLite 與 PostgreSQL 皆支援）在 DB 層保證。
   - 切換時先停用其他設定、再啟用目標，分成兩個語句：索引逐列檢查，在同一個 UPDATE 內互換會依列順序失敗（已在 SQLite 實測）。
   - 並行時後到的請求違反索引：
     - 切換使用中：rollback 後重新讀取並重試一次，仍失敗回 409。
     - 新增第一筆：改為非使用中再新增一次，仍失敗即為名稱重複，回 409。
   - 第一筆設定自動設為使用中；之後新增或編輯都不改變使用中。
   - 使用中的設定不可刪除。
   - 名稱不可重複。
3. **API 金鑰**：
   - 以 Fernet 加密存 DB。另存遮罩值 `api_key_hint`（`sk-…abcd`），列表不必解密。
   - 編輯時金鑰留空表示沿用已存的金鑰。
   - 只在 gateway 呼叫當下解密。
4. **ChatGPT 訂閱登入**：
   - LiteLLM 內建的裝置碼登入會 `print` 驗證碼，並以 `time.sleep` 阻塞整個請求（最久 15 分鐘），無法用在網頁。
   - `services/llm/chatgpt_auth.py` 改為重用 LiteLLM `Authenticator` 的各個步驟：取得驗證碼後立即回給網頁；輪詢與換發 token 在背景執行緒完成。
   - token 寫入 LiteLLM 讀取的同一個檔案（`CHATGPT_TOKEN_DIR`，預設 `backend/data/chatgpt/auth.json`）。
   - 呼叫 `chatgpt/` 模型前先確認 token 可用，必要時先換發；失敗就回「請重新登入」，不讓 LiteLLM 進入阻塞式登入。
   - 為此放寬規則：除了 `gateway.py`，`chatgpt_auth.py` 也可 import `litellm.llms.chatgpt`，但只用於登入。
5. **測試對話**：
   - 取代 llm.md 原本的「固定短 prompt 測試連線」。
   - `POST /api/v1/llm-configs/{id}/chat` 以 SSE 串流回應，事件為 `delta`、`done`（附模型、總耗時、首字時間、token 數）、`error`。
   - 串流在 dependency 中開啟，所以金鑰無效、找不到模型等錯誤會在回應開始前以 HTTP 錯誤回傳；串流途中的錯誤才轉成 `error` 事件。
   - 對話歷史只存在前端，每次送出完整歷史；後端不保存對話，也不寫入 log。
   - 不帶 `temperature`，因為部分 Codex 模型只接受預設值；其他不支援的參數由 `drop_params` 移除。
   - LiteLLM 例外一律轉成繁中、可操作的訊息，不回傳原始例外字串。
6. **模型下拉選單與本地伺服器自動判斷**：
   - 使用者不知道服務有哪些模型，所以模型名稱改為下拉選單，由後端即時查詢各服務的模型清單。
   - 使用者也分不清 Ollama 與 OpenAI 相容伺服器，所以畫面上合併為「本地模型」，由後端偵測實際類型。
   - ChatGPT 訂閱：不用 LiteLLM 內建清單（會缺新模型、列出帳號不能用的舊模型），改以登入 token 查詢此帳號在 Codex 模型選單上的模型；呼叫時一律用 `chatgpt/responses/<模型>`，否則不在 LiteLLM 內建清單的新模型會被送到 Codex 後端不支援的 `/chat/completions`。
   - 清單查詢以 httpx 實作（`model_catalog.py`），流程與金鑰解析在 `model_listing.py`。
   - Codex 後端依 `client_version` 篩選模型，版本太舊時新模型（例如 gpt-6.1-sol）不會列出。版本由 `codex_version.py` 自動取得 npm `@openai/codex` 的最新版本（記憶體快取一天；失敗時改用 `CHATGPT_CLIENT_VERSION_FALLBACK`，並在 10 分鐘內不再重試），`CHATGPT_CLIENT_VERSION` 可手動固定。不採用本機 `codex --version`（伺服器不一定有安裝，版本也可能舊），也不送虛構的高版本號（可能列出目前呼叫方式尚未支援的模型）。
7. **逐步工作表**：新增與編輯都用彈出式工作表，一步一頁（服務類型 → 連線設定 → 選擇模型 → 命名與確認）；每一步只檢查該步欄位，最後一步才儲存。
8. **內網**：LiteLLM 預設會在 import 時從 GitHub 下載模型價格表。`services/llm/__init__.py` 設定 `LITELLM_LOCAL_MODEL_COST_MAP=True`，改用套件內建的價格表。

## 影響

- **好處**：
  - 可同時保存 Codex、Gemini 與本地模型的設定，隨時切換。
  - 設定畫面與實際呼叫走同一個 gateway，測試結果能代表實際行為。
- **代價與風險**：
  - ChatGPT 訂閱登入依賴 LiteLLM 的私有方法。版本以 `==` 鎖定，`tests/services/llm/test_chatgpt_auth.py` 會檢查這些方法是否仍存在，升級時要重新確認。
  - ChatGPT 登入 token 以明文存在 `backend/data/`（不進版控）。token 目錄權限為 0700、檔案為 0600，只有後端程序的擁有者可以讀寫。LiteLLM 也會自行重寫這個檔案，所以以目錄權限為主要保護。取得真實資料或部署到共用主機前，須重新評估是否要加密或改用其他登入方式。
  - 登出與寫入 token 檔（登入完成、換發 token）以同一把 `asyncio.Lock` 互斥，避免登出後 token 又被寫回；換發也因此不會以同一個 refresh token 同時進行（OpenAI 會輪替 refresh token）。
  - 持鎖的操作在獨立的背景 task 中執行，呼叫端以 `asyncio.shield` 等待（`chatgpt_auth._run_exclusively`）：請求被取消時，檔案操作的執行緒無法中止，鎖要等執行緒跑完才釋放。
  - 進行中的裝置碼登入只存在單一後端程序的記憶體中；後端重新啟動後需重新登入。
  - 測試對話會把輸入內容送到所選服務。畫面上已提示「請勿輸入病患資料」，PHI 外送政策仍依 [ADR 0002](0002-llm-phi-policy.md)。
- **後續**：
  - 登入與權限確定後，設定頁要加權限控管，並在 `setting_change_logs.actor` 記錄操作者。
  - 稽核規則實作時，由 gateway 讀取使用中的設定（`complete_structured`）。
