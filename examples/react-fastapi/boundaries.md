# ② 系統邊界

## 範圍
- 範圍內：單筆訂單的折扣計算 API，以及輸入金額、顯示結果的前端表單。
- 範圍外（明確不做）：登入與會員資格查詢（`is_member` 由使用者勾選）、資料庫與歷史紀錄、幣別與稅金、CORS 與部署設定。

## 邊界條目

| 編號 | 邊界 | 驗證方式 |
|---|---|---|
| B1 | API 合約：`POST /api/discount`，request body `{"amount": number, "is_member": boolean}`，成功回 200 與 `{"final_price": number}`。 | 測試 |
| B2 | 信任邊界：輸入驗證只在 router 層（Pydantic model）完成，驗證失敗回 422；service 與 domain 假設輸入合法，不重複驗證。 | 審查 |
| B3 | 前端不自行計算折扣，畫面上的應付金額一律是 `calculate` 回傳的值。 | 測試 |
| B4 | `calculateDiscount` 在 HTTP 狀態不是 200 時拋出錯誤；`DiscountForm` 收到錯誤時以 `role="alert"` 顯示「計算失敗」，且不顯示應付金額。 | 測試 |
| B5 | 不使用資料庫、檔案或任何外部服務；不保存任何資料。 | 審查 |
| B6 | 測試中不發出真實網路請求：後端用 `TestClient`，前端以 props 傳入假的 `calculate`，`calculateDiscount` 本身以替換 `fetch` 的方式測試。 | 審查 |
