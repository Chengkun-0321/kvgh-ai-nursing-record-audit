# 資安與隱私規範

## 資料分級

| 資料 | 處理方式 |
|---|---|
| 自製虛構病房資料包 `mock_data/` | 完全虛構（人員只用代碼、不取材自院內截圖內容），可進版控 |
| 院方假資料 | 視同敏感資料：只放 `backend/data/`，不進版控、不外傳 |
| 真實病患資料 | 目前未取得；取得前須先完成 [ADR 0002](../adr/0002-llm-phi-policy.md) 的重新評估 |
| 測試 fixture | 必須完全虛構，可進版控 |

## 機密管理

- 機密只放 `.env`（不進版控）；`.env.example` 列出所有變數與說明（不含真值）
- 程式一律經 `Settings` 讀取，不直接讀 `os.environ`
- LLM API key 加密存 DB、只回傳遮罩值，細節見 [llm.md](llm.md)
- ChatGPT 訂閱登入的 token 以明文存在 `backend/data/chatgpt/`（不進版控；目錄 0700、檔案 0600）；部署到共用主機或接真實資料前須重新評估（見 [ADR 0006](../adr/0006-llm-config-settings.md)）
- 設定頁的測試對話會把輸入內容送往所選服務：畫面提示勿輸入病患資料，後端不保存、不記錄對話內容

## Log 與錯誤訊息

- 只可記錄 `patient_key`（內部匿名鍵）、`record_id`、規則代碼、批次 ID
- 禁止記錄：姓名、病歷號、身分證字號、生日、電話、地址、紀錄全文
- 例外訊息、API 錯誤回應同樣適用；前端不顯示 stack trace

## PHI 外送 LLM

- 目前（假資料階段）不限制，決策見 [ADR 0002](../adr/0002-llm-phi-policy.md)
- gateway 保留 `preprocess` hook，未來可插入去識別化
- **接真實資料前必須重新評估並新增 ADR**

## API

- CORS 只允許 `Settings.CORS_ORIGINS` 內的來源，禁止 `*`；瀏覽器經 Next.js 同網域轉送呼叫後端（[ADR 0011](../adr/0011-same-origin-api-proxy.md)），不因對外網域而放寬 CORS
- 所有輸入經 Pydantic 驗證；路徑參數（如日期）驗證格式，防止 path traversal
- SQL 一律經 SQLAlchemy 或 bound parameters，禁止字串拼接

## 身分驗證與操作紀錄

- 登入與權限機制**待決**（開發階段無登入）；上線前 LLM 設定頁必須有權限控管
- LLM 設定變更寫入 `setting_change_logs`：時間、操作者、變更欄位（不含 key 值）

## 依賴

- 只使用 backend／frontend CLAUDE.md 的核准清單；新增需說明理由並取得同意
- 版本精確鎖定（`==`、`--save-exact`），套件只裝在專案內
