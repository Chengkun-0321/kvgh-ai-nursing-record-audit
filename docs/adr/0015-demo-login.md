# ADR 0015：Demo 固定帳密登入（後端驗證、所有 API 需登入）

- 狀態：採用（暫行；正式登入與權限仍待決）
- 日期：2026-11-25

## 背景

系統於 2026-11-25 部署到對外網址（見 [deployment-docker.md](../deployment-docker.md)），之前沒有任何登入：連得到網址的人可使用全部功能，包括 LLM 模型設定（含 API key）與稽核。正式的使用者登入與權限仍是待決事項，但展示期間需要先擋住無關的連線者。使用者決定採用單一固定帳密、不提供註冊，帳密存在 `.env`，不寫進程式碼（避免隨 repo 外流）。

## 決策

1. **後端驗證，前端只負責畫面**（沿用 [ADR 0009](0009-backend-owns-computation.md)）：帳密只在後端比對；只做前端登入頁擋不住直接呼叫 `/api/v1/...`。
2. 帳密來自後端設定 `DEMO_LOGIN_USERNAME`、`DEMO_LOGIN_PASSWORD`（`backend/.env`），**必填、無預設值**；缺少時後端無法啟動（fail closed）。比對用固定時間比較（`hmac.compare_digest`）。
3. 登入狀態以 HttpOnly cookie `kvgh_session` 保存：內容為帳號、到期時間與 HMAC-SHA256 簽章，簽章金鑰由既有 `LLM_KEY_ENCRYPTION_KEY` 衍生，不新增設定與依賴；有效期 `SESSION_MAX_AGE_SECONDS`（預設 12 小時）。後端不存 session，登出只清除瀏覽器 cookie。
4. API：`POST /api/v1/auth/login`、`POST /api/v1/auth/logout`、`GET /api/v1/auth/session`；其餘 `/api/v1/*` 未登入一律回 401「請先登入」。
5. 前端：`/login` 頁（標題「AI 護理稽核系統 demo」）；`proxy.ts` 在沒有 cookie 時把頁面導到 `/login?next=…`（只看 cookie 是否存在，真正驗證在後端）；`next` 只接受站內路徑；Server Component 呼叫後端時轉送使用者的 cookie；收到 401 導回登入頁。頂部顯示登入帳號並提供登出。

## 影響

- 不知道帳密的人只能看到登入頁，API 也無法直接呼叫。
- **只是 demo 等級**：單一共用帳號、沒有錯誤次數鎖定、沒有權限分級、無法撤銷已發出的 cookie（改密碼不會讓已登入者登出；更換 `LLM_KEY_ENCRYPTION_KEY` 才會，但同時會使已存的 API key 無法解密）。正式上線前須另立 ADR 取代本決策。
- cookie 未設 `Secure`（本機開發為 http）；對外部署只開 HTTPS 入口，影響有限。
- 部署時 `backend/.env` 必須新增兩個變數，否則後端啟動失敗。
- 本機開發前端 3000 → 後端 8000 為跨來源，後端 CORS 開啟 `allow_credentials`，`CORS_ORIGINS` 仍禁止 `*`。
