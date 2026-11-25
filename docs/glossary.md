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
| 入院日期   | `admission_date`      | 只有日期（病床總覽、住院天數用）；入院規則的稽核日                |
| 入院時間   | `admitted_at`         | 含時刻的入院時間（院方「入院時間」）；`admitted_at_text` 為院方原文     |
| 住院天數   | `length_of_stay_days` | 業務日期與入院日期相差的日數                                            |
| 診斷       | `diagnosis`           |                                                                         |
| 住院       | `admission`           | 一次住院期間                                                            |
| 護理長     | `head_nurse`          |                                                                         |
| 護理師     | `nurse`               |                                                                         |
| 目前使用者 | `current_user`        | 登入的使用者；目前為 demo 固定帳號（[ADR 0015](adr/0015-demo-login.md)），正式權限待決 |
| 登入狀態   | `session`             | 登入後由後端發出的簽章 cookie `kvgh_session`，有效期 `SESSION_MAX_AGE_SECONDS` |

## 護理紀錄與臨床資料

| 中文             | 英文識別字                  | 說明                                         |
| ---------------- | --------------------------- | -------------------------------------------- |
| 護理紀錄（總稱） | `nursing_record`            |                                              |
| 入院護理評估     | `admission_assessment`      |                                              |
| 入院經過         | `admission_course`          | 發生時間、不適症狀、就醫經過、處理、住院原因 |
| 每日身體評估     | `daily_physical_assessment` | 院方「每日身評」；最新快照，日期以紀錄時間為準（ADR 0011） |
| 護理過程紀錄     | `nursing_progress_note`     |                                              |
| 轉出摘要         | `transfer_out_summary`      | 院方資料目前沒有（R05 預留）                 |
| 轉入摘要         | `transfer_in_summary`       | 院方資料目前沒有（R05 預留）                 |
| 生命徵象         | `vital_sign`                |                                              |
| 醫囑             | `medical_order`             | 不用 `order`，避免與排序混淆                 |
| 藥囑             | `medication_order`          |                                              |
| 給藥紀錄         | `medication_administration` | 院方資料目前沒有給藥執行紀錄（R07 預留）     |
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
| 稽核規則   | `audit_rule`     | 代碼 R01–R11。R01–R04、R06 已實作；R05、R07 預留（不呼叫 LLM）；R08–R11 候選。見 [audit-rules.md](conventions/audit-rules.md) |
| 稽核週期 | `audit_cycle` | `once_per_admission`（入院時；R01、R03 稱「入院規則」，ADR 0013）／`daily`（每日）／`event`（事件；R06 依所選稽核日追蹤範圍內會診，ADR 0012） |
| 稽核日 | `effective_business_date` | 結果寫入與查詢日期：入院規則為入院日，缺入院日則為所選日期；其他規則為所選日期。所選日期須已結束 |
| 已結束的稽核日 | `is_day_ended` | 稽核日早於今天（Asia/Taipei）。未結束的日期不可稽核，可稽核性為 `day_not_ended`（「當日尚未結束」），API 回 409 不寫入（ADR 0012；實作於 `services/audit/clock.py`） |
| 期限到期日 | `deadline` | R06 每筆會診日加追蹤期限天數；不一定等於稽核日 |
| 會診日 | `business_date`（會診紀錄） | R06 每筆會診的歸日，追蹤期限從此日起算 |
| 追蹤期限 | `AUDIT_CONSULT_FOLLOWUP_DAYS` | R06 從會診日至會診日加此日曆天數，兩端均含；預設 1，待院方確認 |
| 稽核執行   | `audit_run`      | 一次稽核執行，對應 `audit_runs` 一列；重跑新增一列，不覆蓋。入院規則已完成後仍可單項重跑（ADR 0013）           |
| 執行狀態   | `audit_run_status` | 一次執行的狀態，四個值：`COMPLETED`（已完成）、`NOT_APPLICABLE`（當日無此事件）、`DATA_UNAVAILABLE`（院方尚未提供資料）、`FAILED`（執行失敗） |
| 稽核中     | `is_running`     | 某項稽核正在後端執行、尚未寫入結果；登記在後端記憶體，不是 `audit_run_status` 的值（ADR 0011 決策 9） |
| 可稽核性 | `availability` | 四個值：`available`、`not_applicable`、`data_unavailable`、`day_not_ended`；最後一項由服務層判斷 |
| 寬限期中 | `IN_GRACE` | R06 逐筆會診尚未到期且未見對應紀錄的狀態，該筆判定 `PASS`；不是可稽核性 |
| 稽核發現   | `audit_finding`  | 一次執行中的一個發現（項目、判定、訊息、Evidence），對應 `audit_findings` 一列 |
| 判定       | `verdict`        | `PASS` / `WARNING` / `NEEDS_REVIEW`；`ERROR` 列舉保留，LLM 不產生（見 ADR 0011） |
| 最嚴重判定 | `worst_verdict`  | 一床各規則最新一次已完成結果中最嚴重者，決定病床總覽的狀態（嚴重度排序見 `services/audit/severity.py`） |
| 可稽核規則數 | `auditable_rule_count` | 病床總覽中所選日期已結束且規則可執行的數量；R06 範圍內只有寬限期中會診仍計入 |
| 已稽核規則數 | `audited_rule_count` | 可稽核規則中，最新一次執行為 `COMPLETED` 的數量（最新一次為 `FAILED` 不算） |
| 稽核格狀態 | `RuleCellState` | 首頁每位病患各規則的呈現狀態；包含執行中、四種判定、執行失敗、不可用與尚未稽核（ADR 0014） |
| 欄標題短名 | `short_name` | 規則提供的繁中短名，用於首頁清單欄標題；完整名稱與代碼仍提供提示 |
| 稽核進度   | `audit_progress_text` | 病床上的進度文字，例：「已稽核 4／4 項」，由後端產生            |
| 病房地圖   | `ward_map`       | 病床總覽的可拖曳、縮放 3D 場景，詳情與篩選控制固定於場景外    |
| 病房場景   | `ward_scene`     | 病房地圖底層的 3D 畫面，由場景模組依床數組成                  |
| 場景模組   | `kit_module`     | Blender 產生的可拼接 GLB（床位空間、側走道、前緣）            |
| 床位空間   | `bay`            | 一張床與其周邊設施所占的模組（寬 2.4 m、排距 4.2 m）          |
| 空床位     | `vacant_bay`     | 版面補齊欄數後沒有病床的床位空間，不放床下陰影                |
| 床頭隔屏   | `headwall_spine` | 第 1 排起床位背後的矮隔屏（取代後牆），上有設備帶             |
| 病床總覽   | `bed_board`      | 首頁：病房內各床的稽核狀態                                    |
| 待處理病床 | `pending_bed`    | 已稽核且最嚴重判定不是 `PASS` 的病床                          |
| 病床狀態   | `bed_board_status` | 病床總覽每床顯示的狀態：四種判定之一，或 `NOT_AUDITED`（計算見 `services/ward_board_status.py`） |
| 尚未稽核   | `not_audited`    | 該床還沒有稽核結果（不是判定等級，Verdict 分級仍待決）        |
| 紀錄時間   | `recorded_at`    | 稽核結果相關護理紀錄的紀錄時間                                |
| 證據       | `evidence`       | 判定依據：來源、紀錄 ID、欄位、日期、原文片段。LLM 只給紀錄 ID 與原文片段，其餘由程式依 ID 回填 |
| 來源紀錄   | `source_record`  | 可被 LLM 引用的一筆紀錄（`record_id`、來源類別、日期、欄位）；Evidence 只能指向本次提供的來源紀錄 |
| 紀錄 ID    | `record_id`      | 院方資料沒有紀錄 ID：時間軸紀錄用內容雜湊 `event_id`；工作清單用 `work_checklist-<雜湊>`（ADR 0011） |
| 規則專屬資料 | `details`      | 結果中規則專屬的欄位（例：R01 `elements`、R04 `flagged_items`），加上程式算出的 `facts` |
| 程式事實   | `facts`          | 規則由程式整理、要存入 `details` 的資料，不經 LLM（例：R02 相似度參考值） |
| 相似度參考值 | `similarity`   | R02 程式算出的字元比率（0–1，兩位小數）。只供 LLM 參考，不設門檻，不是判定依據 |
| 判定引擎   | `engine`         | **已廢止**（ADR 0011）：七項稽核一律經 LLM 判定，不再區分 `rule`／`llm`／`hybrid` |
| 業務日期   | `business_date`  | 稽核歸屬日，以 Asia/Taipei 計算。紀錄歸日依紀錄本身的時間，不依資料夾日期（ADR 0011） |

## LLM 設定與呼叫

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
| 結構化呼叫       | `complete_structured` | 要求 JSON 輸出、以 `output_schema` 驗證後回傳；格式不符時附錯誤重試（見 [llm.md](conventions/llm.md)） |
| 規則 prompt      | `prompt`             | `app/prompts/<prompt_name>/v<N>.j2`，每項稽核一個目錄，每個版本一個檔案 |
| prompt 名稱      | `prompt_name`        | prompt 目錄名稱，例：`r03_admission_completeness`                    |
| prompt 版本      | `prompt_version`     | 規則 prompt 的版本號 `v<N>`，稽核結果據此重現；已產出結果的版本不就地修改 |
| 輸入摘要         | `input_digest`       | 渲染後 prompt 的 sha256；只存摘要，不存全文                          |
| 格式重試         | `LLM_MAX_RETRIES`    | 輸出不符合 `output_schema` 時附上錯誤重試的次數（不含第一次呼叫）     |
| 網路重試         | `LLM_STRUCTURED_NUM_RETRIES` | 網路錯誤、429、逾時的重試次數（LiteLLM `num_retries`），與格式重試分開 |
| 輸出上限         | `LLM_MAX_OUTPUT_TOKENS` | 稽核每次呼叫模型的輸出 token 上限；達上限被截斷時不重試，該項判為需人工確認（NEEDS_REVIEW） |

## 院方原始資料（見 [ADR 0010](adr/0010-hospital-raw-data-viewer.md)）

| 中文           | 英文識別字            | 說明                                                                       |
| -------------- | --------------------- | -------------------------------------------------------------------------- |
| 原始資料       | `raw_data`            | 院方每日傳送、未經轉換的病人資料檔；原始資料頁照原樣呈現                   |
| 資料日期       | `business_date`       | 院方資料資料夾的日期（`<YYYYMMDD>`），程式中的識別字與稽核歸屬日相同。兩者意義不同：稽核歸日依紀錄本身的時間，不用資料夾日期（ADR 0011） |
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
