# ADR 0014：首頁預設病患清單與逐項稽核狀態，保留 3D 病房切換

- 狀態：採用
- 日期：2026-11-25

## 背景

護理長在 2026-11-20 會議要求「一個畫面看完」：每列病患接各項稽核燈號，避免逐床開啟詳情才能了解各項狀態。既有首頁以 3D 病房呈現，只提供整體判定與非 PASS 發現，因此將 3D 改為可切換檢視，預設改用病患清單。

## 決策

1. `GET /api/v1/wards/{ward_code}/bed-board` 新增 `rules` 欄標題（`rule_code`、`name`、`short_name`），每床新增七個 `rule_cells`（`rule_code`、`state`、`label`、`verdict`、`finding_count`）；兩者皆依 `RULE_REGISTRY` 順序。`short_name` 由規則類別宣告；不改 DB schema。
2. 後端在 `ward_board_status.py` 依以下順序決定格子，符合即停止：
   - 共用的 `RUNNING_AUDITS` 登記為執行中：`RUNNING`。鍵為病患、規則、該規則稽核日，入院規則使用入院日。
   - 該稽核日最新一次為 `COMPLETED`：依 Verdict 顯示四種判定，文字用 `VERDICT_LABELS`，計算該次非 PASS 發現數。
   - 最新一次為 `FAILED`：執行失敗。
   - 最新一次為 `NOT_APPLICABLE`／`DATA_UNAVAILABLE`：顯示對應狀態與既有執行狀態文字。
   - 沒有執行紀錄且 availability 非 AVAILABLE：顯示不適用、院方未提供資料或稽核日未結束，沿用可用性標籤。
   - 其餘為 `NOT_AUDITED`。
   只有已完成結果帶 verdict 與非 PASS 發現數，其餘 verdict 為 null、數量為 0。執行中先於舊結果，以免重跑時誤認已結束；已完成先於當日可用性，沿用 ADR 0011 決策 8「已完成結果不要求當日仍可稽核」。
3. 保留最新一次任何狀態供格子使用；既有床位整體狀態、pending_findings、摘要、進度與狀態列數字的意義不變。沿用 `list_latest_runs` 批次查詢，不逐床逐規則查 DB。純函式由呼叫端注入執行中查詢，與 `AuditService` 使用同一份行程共用登記。
4. 預設清單，使用者可切換 3D 病房；localStorage 記住選擇，讀寫包 try/catch，讀不到或值無效即清單。僅在選擇病房時偵測 WebGL，不支援或載入失敗時沿用 2D 病床格。清單及病房共用選取與詳情。切換膠囊以 portal 放進頂部導覽預留的插槽（桌機在使用者狀態膠囊左側，手機在頂列使用者狀態左側），狀態仍由首頁持有。底部狀態列（依判定淡化篩選）只在 3D 病房顯示；清單已逐格列出結果，不顯示狀態列、不篩選（2026-11-25 使用者決定）。
5. 清單每格使用圖示、後端文字及發現數，顏色不是唯一辨識；窄螢幕可水平捲動並固定床號欄。桌機開既有詳情大卡，手機開既有 sheet。
6. 任一格為 `RUNNING` 時，每 `AUDIT_RUNNING_POLL_MS` 呼叫 `router.refresh()`；全部結束、病房／日期改變或元件卸載時清除計時器。沿用 ADR 0011 決策 9 的單行程登記限制。

## 影響

- 護理長能直接掃讀各床七項狀態；3D 與原有詳情仍可使用，篩選只在 3D 病房。
- API 新欄位增加回應大小；前端型別須以 `npm run gen:api` 重新產生。
- 後端為格子狀態唯一判斷來源，前端只對應圖示與樣式；稽核規則、prompt、DB schema 與依賴不變。
- 執行中才輪詢，完成後停止；依然受單一後端行程限制，多 worker 的共享登記另案處理。
