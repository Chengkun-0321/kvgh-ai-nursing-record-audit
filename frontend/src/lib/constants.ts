// 病房選擇與登入權限仍待決，首頁暫以固定病房呈現
export const DEFAULT_WARD_CODE = "W51";

// 與 Tailwind `lg` 斷點一致：以上顯示右側詳情面板，以下改用 bottom sheet
export const DESKTOP_MEDIA_QUERY = "(min-width: 64rem)";

// 頂列時鐘只顯示到分鐘，每 30 秒更新即可（60 為其倍數，不會跨分鐘誤差）
export const CLOCK_TICK_MS = 30_000;

// ChatGPT 裝置碼登入：OpenAI 建議的輪詢間隔為 5 秒
export const CHATGPT_LOGIN_POLL_MS = 5_000;

// 測試對話一次最多送出的訊息數，與 backend/app/core/constants.py 的 CHAT_MAX_MESSAGES 一致
export const CHAT_MAX_MESSAGES = 40;
export const CHAT_MAX_MESSAGE_CHARS = 8_000;

// 共用 system prompt 字數上限，與 backend/app/core/constants.py 的 LLM_SYSTEM_PROMPT_MAX_CHARS 一致
export const SYSTEM_PROMPT_MAX_CHARS = 8_000;

// 模型清單：輸入 API 位址或金鑰停頓後才查詢，避免每打一個字就呼叫一次
export const MODEL_LIST_DEBOUNCE_MS = 500;

// 護理紀錄頁讀取的假資料目錄（相對於 frontend/，可用伺服器端環境變數 MOCK_DATA_DIR 覆寫）
export const DEFAULT_MOCK_DATA_DIR = "../mock_data";
