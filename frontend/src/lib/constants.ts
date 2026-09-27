// 病房選擇與登入權限仍待決，首頁暫以固定病房呈現
export const DEFAULT_WARD_CODE = "W51";

// 與 Tailwind `lg` 斷點一致：以上顯示右側詳情面板，以下改用 bottom sheet
export const DESKTOP_MEDIA_QUERY = "(min-width: 64rem)";

// 頂列時鐘只顯示到分鐘，每 30 秒更新即可（60 為其倍數，不會跨分鐘誤差）
export const CLOCK_TICK_MS = 30_000;
