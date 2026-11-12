// 與 Tailwind `lg` 斷點一致：以上顯示右側詳情面板，以下改用 bottom sheet
export const DESKTOP_MEDIA_QUERY = "(min-width: 64rem)";

// 頂列時鐘只顯示到分鐘，每 30 秒更新即可（60 為其倍數，不會跨分鐘誤差）
export const CLOCK_TICK_MS = 30_000;

// ChatGPT 裝置碼登入：OpenAI 建議的輪詢間隔為 5 秒
export const CHATGPT_LOGIN_POLL_MS = 5_000;

// 設定精靈：停止輸入一段時間後才請後端檢查表單（並據以查詢模型清單），避免每打一個字就呼叫一次
export const DRAFT_CHECK_DEBOUNCE_MS = 500;
