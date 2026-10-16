# 領域詞彙表

程式識別字（變數、欄位、資料表、API 路徑）一律使用下表英文名。同一概念只用一個名稱；新增詞彙先補進本表。
院方 JSON 欄位名稱與本表不同時，在匯入正規化時轉換（見 [data-ingestion.md](conventions/data-ingestion.md)）。

## 組織與病患

| 中文       | 英文識別字            | 說明                                                                    |
| ---------- | --------------------- | ----------------------------------------------------------------------- |
| 病房       | `ward`                |                                                                         |
| 病房名稱   | `ward_name`           | 例：內科病房                                                            |
| 病床       | `bed`                 |                                                                         |
| 床號       | `bed_code`            | 例：`W51-1`                                                             |
| 病患       | `patient`             |                                                                         |
| 病患匿名鍵 | `patient_key`         | 系統內部匿名識別，log 只能用這個                                        |
| 病患摘要   | `patient_summary`     | 病床總覽所需的病患基本資料                                              |
| 姓名       | `name`                | 僅供畫面顯示，禁止寫入 log、例外訊息、URL                               |
| 性別       | `sex`                 | `M` / `F`                                                               |
| 年齡       | `age_years`           |                                                                         |
| 年齡層     | `age_group`           | `young`（< 45）/ `middle`（45–64）/ `elder`（≥ 65），僅用於選擇病床圖片 |
| 入院日期   | `admission_date`      |                                                                         |
| 住院天數   | `length_of_stay_days` | 業務日期與入院日期相差的日數                                            |
| 診斷       | `diagnosis`           |                                                                         |
| 住院       | `admission`           | 一次住院期間                                                            |
| 護理長     | `head_nurse`          |                                                                         |
| 護理師     | `nurse`               |                                                                         |
| 目前使用者 | `current_user`        | 登入的使用者（登入機制待決，目前為虛構資料）                            |
| 院方病患代碼 | `patient_id`        | 院方提供的去識別病患代碼，跨日固定；匯入後轉成內部 `patient_key`        |
| 住院序號   | `admission_id`        | 院方提供，區分同一病患的不同次住院                                      |
| 人員代碼   | `staff_id`            | 院方提供的護理師、醫師、營養師代碼（如 `author_id`），不含姓名          |
| 住院狀態   | `status`（patient 內）| `inpatient` / `transferred_out` / `discharged`                          |
| 出院       | `discharge`           |                                                                         |
| 班別       | `shift`               | `day`（白班）/ `evening`（小夜）/ `night`（大夜）                       |

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
| 轉入／轉出       | `transfer`                  | `direction`：`in` / `out`                    |
| 紀錄標籤         | `title_category`            | 過程紀錄標題的分類，如健康問題、會診、營養照會建議、轉出摘要 |
| 營養照會         | `nutrition_consultation`    | 會診中 `consultant_role` 為營養師者          |
| 會診回覆時間     | `replied_at`                | 醫師（營養師）書寫紀錄時間                   |
| 高警訊用藥       | `high_alert_medication`     | 藥囑欄位 `is_high_alert`                     |
| 檢查             | `examination`               | 本次醫囑清單中的檢查，含 `is_invasive`       |
| 情緒困擾評估     | `emotional_distress_assessment` | 一次評估紀錄，內含 `score`               |

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
| 待處理病床 | `pending_bed`    | 最嚴重判定不是 `PASS` 的病床                                  |
| 紀錄時間   | `recorded_at`    | 稽核結果相關護理紀錄的紀錄時間                                |
| 證據       | `evidence`       | 判定依據：來源、紀錄 ID、欄位、日期、原文片段                 |
| 判定引擎   | `engine`         | `rule` / `llm` / `hybrid`                                     |
| 業務日期   | `business_date`  | 稽核歸屬日，以 Asia/Taipei 計算                               |
| 紀錄時間軸 | `record_timeline` | 護理紀錄頁：一位病患所有日期的紀錄，由新到舊排列               |
| 紀錄類型   | `record_type`    | 時間軸的篩選分類：入院評估、每日身體評估、護理紀錄、轉入轉出、給藥紀錄、會診、生命徵象、檢驗 |

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

## 資料匯入

| 中文     | 英文識別字        | 說明               |
| -------- | ----------------- | ------------------ |
| 中繼站   | `relay`           | 院方每日上傳資料處 |
| 匯入批次 | `ingestion_batch` |                    |
| 資料來源 | `data_source`     | `local` / `relay`  |
| 每日資料包 | `daily_package` | 院方每天產出的一個業務日資料夾（`YYYYMMDD/`） |
| 資料包清單 | `manifest`      | 資料包內的 `manifest.json`，列出當天病患檔案 |
| 假資料目錄 | `mock_data`     | 專案根目錄的自製虛構資料包 |

## 開發流程（規格驅動）

見 [spec-flow.md](conventions/spec-flow.md)。以下為流程用語，不是程式識別字。

| 中文         | 英文／代號             | 說明                                                                 |
| ------------ | ---------------------- | -------------------------------------------------------------------- |
| 規格         | `spec`                 | `spec/` 的 architecture.md、boundaries.md、rules.md                   |
| 規格確認     | spec approval          | 人執行 `approve_spec.sh`，把規格與 `flow.config.json` 的雜湊記到 `spec/.approved` |
| 架構約束     | `A*`                   | A1～A7 為專案固定約束，本次功能從 A8 起編                            |
| 系統邊界     | `B*`                   | 範圍、外部介面、API 合約                                             |
| 業務規則     | `BR*`                  | 正常行為；與稽核項目代碼 `R01`～`R11` 不同                           |
| 異常行為     | `E*`                   | 不合法輸入、例外情況的預期行為                                       |
| 一致性報告   | consistency report     | 一致性 Agent 比對規格、測試、程式後的報告（`.flow/report.md`）       |
