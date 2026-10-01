# ADR 0011：瀏覽器經 Next.js rewrites 同網域呼叫後端

- 狀態：提議
- 日期：2026-10-01

## 背景

- 原本瀏覽器以 `NEXT_PUBLIC_API_BASE_URL`（`http://localhost:8000`）直接呼叫後端。
- 經 Cloudflare Tunnel 的對外網域開網頁時發生兩個問題：
  - 對外網域不在 `CORS_ORIGINS` 內，CORS 預檢（OPTIONS）被後端回 400，前端顯示「無法連線到後端服務」。
  - 就算加進 CORS，別台電腦的瀏覽器連 `localhost:8000` 是連到自己的機器，只有架站那台 Mac 能用。

## 決策

1. **同網域轉送**：`next.config.ts` 以 rewrites 把 `/api/v1/:path*` 轉到伺服器端的 `API_BASE_URL`。
   - 瀏覽器一律呼叫同網域的 `/api/v1/*`（`lib/api/client.ts` 在瀏覽器端用空字串當 base URL）。
   - Server Component 照舊直接連 `API_BASE_URL`。
   - 移除 `NEXT_PUBLIC_API_BASE_URL`。後端位址不再內嵌到瀏覽器程式。
2. **關閉 Next.js 壓縮**（`compress: false`）：實測 Next.js 內建的 gzip 會把 `text/event-stream` 整段緩衝到結束才送出，測試對話無法逐字顯示。對外網域由 Cloudflare 等前端代理壓縮。
3. **錯誤訊息**：後端的錯誤一律回 JSON `detail`。所以非 JSON 的 5xx（Next.js 轉送失敗、Tunnel 502）顯示「無法連線到後端服務」。
4. **CORS 不放寬**：後端 `CORS_ORIGINS` 維持只有本機開發來源。

## 影響

- **好處**：不需要依網域調整 CORS；從任何網域、任何電腦開網頁都能使用。
- **代價**：
  - 轉送目標在 `next build` 時決定，改 `API_BASE_URL` 需重新建置。
  - Next.js 轉送的閒置逾時預設 30 秒。SSE 由後端每 15 秒送 keep-alive，不受影響；非串流的請求若超過 30 秒會被中斷。
- **注意**：開發階段沒有登入機制（待決事項）。經對外網域開放等於公開 LLM 設定 API 與測試對話，上線或分享網址前必須先有權限控管（[security-privacy.md](../conventions/security-privacy.md)），例如以 Cloudflare Access 限定使用者。
