# 領域詞彙表

程式識別字（變數、欄位、資料表、API 路徑）一律使用下表英文名。同一概念只用一個名稱；新增詞彙先補進本表。
院方 JSON 欄位名稱與本表不同時，在匯入正規化時轉換（見 [data-ingestion.md](conventions/data-ingestion.md)）。

## 組織與病患

| 中文 | 英文識別字 | 說明 |
|---|---|---|
| 病房 | `ward` | |
| 病房名稱 | `ward_name` | 例：內科病房 |
| 病床 | `bed` | |
| 床號 | `bed_code` | 例：`W51-1` |
| 病患 | `patient` | |
| 病患匿名鍵 | `patient_key` | 系統內部匿名識別，log 只能用這個 |
| 病患摘要 | `patient_summary` | 病床總覽所需的病患基本資料 |
| 姓名 | `name` | 僅供畫面顯示，禁止寫入 log、例外訊息、URL |
| 性別 | `sex` | `M` / `F` |
| 年齡 | `age_years` | |
| 年齡層 | `age_group` | `young`（< 45）/ `middle`（45–64）/ `elder`（≥ 65），僅用於選擇病床圖片 |
| 入院日期 | `admission_date` | |
| 住院天數 | `length_of_stay_days` | 業務日期與入院日期相差的日數 |
| 診斷 | `diagnosis` | |
| 住院 | `admission` | 一次住院期間 |
| 護理長 | `head_nurse` | |
| 護理師 | `nurse` | |
| 目前使用者 | `current_user` | 登入的使用者（登入機制待決，目前為虛構資料） |

## 護理紀錄與臨床資料

| 中文 | 英文識別字 | 說明 |
|---|---|---|
| 護理紀錄（總稱） | `nursing_record` | |
| 入院護理評估 | `admission_assessment` | |
| 入院經過 | `admission_course` | 發生時間、不適症狀、就醫經過、處理、住院原因 |
| 每日身體評估 | `daily_physical_assessment` | |
| 護理過程紀錄 | `nursing_progress_note` | |
| 轉出摘要 | `transfer_out_summary` | |
| 轉入摘要 | `transfer_in_summary` | |
| 生命徵象 | `vital_sign` | |
| 醫囑 | `medical_order` | 不用 `order`，避免與排序混淆 |
| 藥囑 | `medication_order` | |
| 給藥紀錄 | `medication_administration` | |
| 會診 | `consultation` | |
| 侵入性檢查／治療 | `invasive_procedure` | |
| 護理指導／衛教 | `health_education` | |
| 同意書 | `consent_form` | |
| 情緒困擾分數 | `emotional_distress_score` | |
| 管路 | `tube` | |
| 檢驗結果 | `lab_result` | |
| 護理計畫 | `nursing_care_plan` | |

## 稽核

| 中文 | 英文識別字 | 說明 |
|---|---|---|
| 稽核規則 | `audit_rule` | 代碼 R01–R11，見 [audit-rules.md](conventions/audit-rules.md) |
| 稽核批次 | `audit_run` | 一次每日稽核執行 |
| 稽核結果 | `audit_finding` | 每位病患 × 每條規則一筆 |
| 判定 | `verdict` | `PASS` / `WARNING` / `ERROR` / `NEEDS_REVIEW` |
| 最嚴重判定 | `worst_verdict` | 一床所有稽核結果中最嚴重者，決定病床總覽的狀態顯示 |
| 病床總覽 | `bed_board` | 首頁：病房內各床的稽核狀態 |
| 待處理病床 | `pending_bed` | 最嚴重判定不是 `PASS` 的病床 |
| 紀錄時間 | `recorded_at` | 稽核結果相關護理紀錄的紀錄時間 |
| 證據 | `evidence` | 判定依據：來源、紀錄 ID、欄位、日期、原文片段 |
| 判定引擎 | `engine` | `rule` / `llm` / `hybrid` |
| 業務日期 | `business_date` | 稽核歸屬日，以 Asia/Taipei 計算 |

## 資料匯入

| 中文 | 英文識別字 | 說明 |
|---|---|---|
| 中繼站 | `relay` | 院方每日上傳資料處 |
| 匯入批次 | `ingestion_batch` | |
| 資料來源 | `data_source` | `local` / `relay` |
