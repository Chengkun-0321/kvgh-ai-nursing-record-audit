# ADR 0010：護理紀錄頁由前端伺服器直接讀取 mock_data

- 狀態：提議
- 日期：2026-10-01

## 背景

- 自製假資料 `mock_data/`（[ADR 0009](0009-hospital-daily-data-format.md)）只能直接開 JSON 看，不方便閱讀。使用者希望在導覽列新增一個分頁，在網頁上瀏覽這些紀錄。
- 後端的資料匯入（`services/ingestion`、DB schema）還沒實作，暫時沒有 API 可以提供這些紀錄。
- 這一頁只讀取、不寫入，資料完全虛構，而且只在開發驗證時使用。

## 決策

1. **讀取方式**：新增 `/nursing-records` 頁，由 Next.js Server Component 經 `src/lib/api/mockDailyPackages.ts` 直接讀取 `mock_data/`。
   - 這是前端唯一的直接讀檔例外，檔頭加上 `import "server-only"`。
   - 目錄由伺服器端環境變數 `MOCK_DATA_DIR` 設定，預設為 `../mock_data`（相對於 `frontend/`）。
2. **防止 path traversal**：
   - 日期資料夾只接受 `^\d{8}$`。
   - 病患檔名只取自 `manifest.json`，並驗證格式，解析後的路徑必須仍在 `MOCK_DATA_DIR` 內。
   - 網址的 `?patient=` 只拿來和 manifest 的 `patient_id` 比對，不直接拼成路徑。
3. **畫面**：
   - 選擇病患後，把所有日期的紀錄攤平成時間軸，由新到舊排列。
   - 左側可勾選紀錄類型：入院評估、每日身體評估、護理紀錄、轉入轉出、給藥紀錄、會診、生命徵象、檢驗。
   - 增量資料依紀錄 ID 去重，藥囑則合併各天的給藥。
4. **只呈現原值**：不判斷正常或異常，也不標示 `mock_data/README.md` 答案表的情境。判斷屬於稽核規則。
5. **導覽**：只在桌機頂部導覽顯示。手機底部分頁列維持 5 項，`NavItemConfig.showInMobileTabBar` 控制。

## 影響

- **好處**：不必等後端匯入完成就能瀏覽假資料；修改 JSON 後重新整理頁面即可看到。
- **代價**：
  - 前端多了一個不經後端的資料來源。
  - 院方資料格式的型別（`src/types/dailyPackage.ts`）目前是依 schema 手寫，格式變更時需要同步修改。
- **後續**：後端完成資料匯入後，改為呼叫後端 API，刪除 `mockDailyPackages.ts` 與手寫型別，改用 `api.ts` 產生的型別。
