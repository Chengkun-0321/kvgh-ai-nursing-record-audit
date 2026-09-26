# 資料匯入規範

## 現況與未來

| 階段 | 來源 | 設定 |
|---|---|---|
| 現在 | 院方提供的假資料 JSON | `DATA_SOURCE=local` |
| 未來 | 院方每日打包上傳中繼站，本系統下載當日資料 | `DATA_SOURCE=relay` |

兩者實作同一介面，切換只改設定，不改匯入流程。

## DataSource 介面

```python
class DataSource(Protocol):
    async def fetch(self, business_date: date) -> list[RawDocument]: ...
```

- `LocalFixtureSource`：讀取 `backend/data/fixtures/<YYYY-MM-DD>/*.json`
- `RelaySource`：傳輸協定、認證方式**待決**；連線資訊只放 `Settings`／`.env`

## 匯入流程

1. `fetch(business_date)` 取得原始檔
2. 原始檔原封保存於 `backend/data/raw/<YYYY-MM-DD>/`，並寫入 `ingestion_batches`（來源、日期、檔名、sha256、狀態）；**原始檔不得修改**
3. checksum 已存在 → 略過（idempotent，重跑同一天不會重複寫入）
4. 以 `app/schemas/ingestion/` 的 Pydantic model 驗證（對應院方格式，含 `schema_version`）
5. 正規化為內部 model（欄位命名依 [glossary.md](../glossary.md)）
6. 入庫：以院方紀錄 ID 等自然鍵判斷新增或更新
7. 輸出批次摘要：成功／失敗／略過筆數

## 錯誤處理

- 單筆驗證失敗 → 寫入 `ingestion_errors`（批次 ID、檔名、JSON path、錯誤訊息，不含病患識別資料）後繼續，不讓整批失敗
- 整個檔案無法解析 → 該批次標記失敗並保留原始檔供排查

## 時間

- 院方時間若無時區資訊 → 視為 Asia/Taipei，轉 UTC 儲存
- `business_date`（稽核歸屬日）一律以 Asia/Taipei 計算

## 格式對照

院方 JSON 格式**待提供**。取得範例後：

1. 先寫 ADR：欄位對照表（院方欄位 → 內部欄位）、必填／選填、特殊值處理
2. 再建立 `schemas/ingestion/` 與對應 models、migration

## 假資料放置

| 類型 | 位置 | 進版控 |
|---|---|---|
| 院方提供的假資料 | `backend/data/fixtures/` | ❌（`backend/data/` 整個被 gitignore） |
| 測試用自製最小資料 | `backend/tests/fixtures/` | ✅（必須完全虛構） |
