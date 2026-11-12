# 領域詞彙表

程式識別字（變數、欄位、資料表、API 路徑）一律使用下表英文名。同一概念只用一個名稱；新增詞彙先補進本表。
院方 JSON 欄位名稱與本表不同時，在匯入正規化時轉換（見 [data-ingestion.md](conventions/data-ingestion.md)）。

## 組織與病患

| 中文       | 英文識別字            | 說明                                                                    |
| ---------- | --------------------- | ----------------------------------------------------------------------- |
| 病房       | `ward`                |                                                                         |
| 病房代碼   | `ward_code`           | 例：`W63`；API 路徑 `/wards/{ward_code}`，格式見 `core/constants.py` 的 `WARD_CODE_PATTERN` |
| 病房名稱   | `ward_name`           | 院方資料未提供；畫面以 `display_name`（如「W63 病房」）顯示             |
| 病床       | `bed`                 |                                                                         |
| 床號       | `bed_code`            | 例：`W63-001`；院方 patientlist 只寫床位（`001`），由後端統一為「病房-床位」 |
| 病患       | `patient`             |                                                                         |
| 病患匿名鍵 | `patient_key`         | 系統內部匿名識別，log 只能用這個；院方資料取 HCASENO（HHISNUM 不使用）  |
| 病患摘要   | `patient_summary`     | 病床總覽所需的病患基本資料                                              |
| 姓名       | `name`                | 僅供畫面顯示，禁止寫入 log、例外訊息、URL                               |
| 性別       | `sex`                 | `M` / `F`                                                               |
| 年齡       | `age_years`           |                                                                         |
| 年齡層     | `age_group`           | `young`（< 45）/ `middle`（45–64）/ `elder`（≥ 65），僅用於選擇病床圖片 |
| 入院日期   | `admission_date`      | 只有日期（病床總覽、住院天數用）                                        |
| 入院時間   | `admitted_at`         | 含時刻的入院時間（院方「入院時間」）；`admitted_at_text` 為院方原文     |
| 住院天數   | `length_of_stay_days` | 業務日期與入院日期相差的日數                                            |
| 診斷       | `diagnosis`           |                                                                         |
| 住院       | `admission`           | 一次住院期間                                                            |
| 護理長     | `head_nurse`          |                                                                         |
| 護理師     | `nurse`               |                                                                         |
| 目前使用者 | `current_user`        | 登入的使用者（登入機制待決，目前為虛構資料）                            |

## 護理紀錄與臨床資料

| 中文             | 英文識別字                  | 說明                                         |
| ---------------- | --------------------------- | -------------------------------------------- |
| 護理紀錄（總稱） | `nursing_record`            |                                              |
| 入院護理評估     | `admission_assessment`      |                                              |
| 入院經過         | `admission_course`          | 發生時間、不適症狀、就醫經過、處理、住院原因 |
| 每日身體評估     | `daily_physical_assessment` |                                              |
| 護理過程紀錄     | `nursing_progress_note`     |                                              |
| 轉出摘要         | `transfer_out_summary`      |                                              |
| 轉入摘要         | `transfer_in_summary`       |                                              |
| 生命徵象         | `vital_sign`                |                                              |
| 醫囑             | `medical_order`             | 不用 `order`，避免與排序混淆                 |
| 藥囑             | `medication_order`          |                                              |
| 給藥紀錄         | `medication_administration` |                                              |
| 會診             | `consultation`              |                                              |
| 侵入性檢查／治療 | `invasive_procedure`        |                                              |
| 護理指導／衛教   | `health_education`          |                                              |
| 同意書           | `consent_form`              |                                              |
| 情緒困擾分數     | `emotional_distress_score`  |                                              |
| 管路             | `tube`                      |                                              |
| 檢驗結果         | `lab_result`                |                                              |
| 護理計畫         | `nursing_care_plan`         |                                              |

## 稽核

| 中文       | 英文識別字       | 說明                                                          |
| ---------- | ---------------- | ------------------------------------------------------------- |
| 稽核規則   | `audit_rule`     | 代碼 R01–R11，見 [audit-rules.md](conventions/audit-rules.md) |
| 稽核批次   | `audit_run`      | 一次每日稽核執行                                              |
| 稽核結果   | `audit_finding`  | 每位病患 × 每條規則一筆                                       |
| 判定       | `verdict`        | `PASS` / `WARNING` / `ERROR` / `NEEDS_REVIEW`                 |
| 最嚴重判定 | `worst_verdict`  | 一床所有稽核結果中最嚴重者，決定病床總覽的狀態顯示            |
| 病房地圖   | `ward_map`       | 病床總覽的可拖曳、縮放 3D 場景，詳情與篩選控制固定於場景外    |
| 病房場景   | `ward_scene`     | 病房地圖底層的 3D 畫面，由場景模組依床數組成                  |
| 場景模組   | `kit_module`     | Blender 產生的可拼接 GLB（床位空間、側走道、前緣）            |
| 床位空間   | `bay`            | 一張床與其周邊設施所占的模組（寬 2.4 m、排距 4.2 m）          |
| 空床位     | `vacant_bay`     | 版面補齊欄數後沒有病床的床位空間，不放床下陰影                |
| 床頭隔屏   | `headwall_spine` | 第 1 排起床位背後的矮隔屏（取代後牆），上有設備帶             |
| 病床總覽   | `bed_board`      | 首頁：病房內各床的稽核狀態                                    |
| 待處理病床 | `pending_bed`    | 已稽核且最嚴重判定不是 `PASS` 的病床                          |
| 病床狀態   | `bed_board_status` | 病床總覽每床顯示的狀態：四種判定之一，或 `NOT_AUDITED`        |
| 尚未稽核   | `not_audited`    | 該床還沒有稽核結果（不是判定等級，Verdict 分級仍待決）        |
| 紀錄時間   | `recorded_at`    | 稽核結果相關護理紀錄的紀錄時間                                |
| 證據       | `evidence`       | 判定依據：來源、紀錄 ID、欄位、日期、原文片段                 |
| 判定引擎   | `engine`         | `rule` / `llm` / `hybrid`                                     |
| 業務日期   | `business_date`  | 稽核歸屬日，以 Asia/Taipei 計算                               |

## LLM 設定

| 中文             | 英文識別字           | 說明                                                                 |
| ---------------- | -------------------- | -------------------------------------------------------------------- |
| 模型設定         | `llm_config`         | 一組 LLM 連線設定（服務類型、模型名稱、API 位址、API 金鑰、逾時）    |
| 服務類型         | `llm_provider`       | `openai` / `chatgpt` / `gemini` / `ollama` / `openai_compatible`     |
| 使用中           | `is_active`          | 同一時間只有一組模型設定為使用中，系統呼叫模型時使用這一組           |
| 金鑰遮罩值       | `api_key_hint`       | 顯示用的遮罩金鑰（如 `sk-…abcd`），明文只在呼叫當下解密              |
| 可用模型         | `available_model`    | 服務目前提供、可選擇的模型（設定頁下拉選單），由後端即時查詢         |
| 本地模型         | `local`              | 畫面上的服務類型選項，涵蓋 `ollama` 與 `openai_compatible`，由後端偵測 |
| 逐步工作表       | `llm_config_wizard`  | 新增／編輯模型設定的彈出式流程，一步一頁                             |
| 測試對話         | `chat_test`          | 設定頁以已儲存的設定直接對話、串流顯示回應；歷史只存在前端           |
| ChatGPT 訂閱登入 | `chatgpt_auth`       | 以 OAuth 裝置碼登入 ChatGPT Plus／Pro，供 `chatgpt` 服務類型使用     |
| 設定變更紀錄     | `setting_change_log` | 設定的新增、更新、切換、刪除紀錄；只記欄位名稱，不記值               |
| 共用 System Prompt | `llm_system_prompt` | 所有模型呼叫（含稽核）都會先帶上的指示，每次儲存為一個新版本       |
| System prompt 版本 | `system_prompt_version` | 呼叫當下使用的共用 system prompt 版本號，稽核結果據此重現       |

## 院方原始資料（見 [ADR 0010](adr/0010-hospital-raw-data-viewer.md)）

| 中文           | 英文識別字            | 說明                                                                       |
| -------------- | --------------------- | -------------------------------------------------------------------------- |
| 原始資料       | `raw_data`            | 院方每日傳送、未經轉換的病人資料檔；原始資料頁照原樣呈現                   |
| 資料日期       | `business_date`       | 院方資料資料夾的日期（`<YYYYMMDD>`），沿用業務日期一詞                     |
| 時間軸         | `timeline`            | 一位病人所有日期的紀錄合併、去重後依時間排列                               |
| 紀錄類別       | `raw_record_category` | 時間軸紀錄對應的院方區塊（護理記錄、生命徵象、檢驗報告…）                 |
| 工作清單       | `work_checklist`      | 院方「工作清單」：入院評估各項是否已填寫（值只有有填寫／沒有填寫）         |
| GCS            | `gcs`                 | 昏迷指數評估（院方區塊名稱）                                               |
| 用藥           | `medication_order`    | 院方「用藥」區塊（藥名、劑量、途徑、頻次），對應藥囑                       |
| 檢查           | `examination`         | 院方「檢查」區塊（影像等檢查報告，含正式／初步報告），會帶出歷史報告       |
| 轉床           | `bed_transfer`        | 院方「轉床資料」區塊                                                       |
| 異常標記       | `abnormal_flag`       | 檢驗值的 `high`／`low`／`abnormal`／`normal`，由院方「異常值」欄轉換       |
| 檢驗矩陣       | `lab_matrix`          | 檢驗報告的項目 × 採檢時間表                                                |

**待確認**：檢驗報告的 `TIME` 項目（12 位數字，推測為血糖測量時間）、項目名為空字串的檢驗（顯示為「（院方未提供項目名）」）。

## 資料匯入

| 中文     | 英文識別字        | 說明               |
| -------- | ----------------- | ------------------ |
| 中繼站   | `relay`           | 院方每日上傳資料處 |
| 匯入批次 | `ingestion_batch` |                    |
| 資料來源 | `data_source`     | `local` / `relay`  |
