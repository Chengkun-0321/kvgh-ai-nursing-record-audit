# 院方每日資料交換格式規格（v0.1.0）

> 對象：高雄榮總資訊處
> 用途：AI 護理紀錄稽核系統每天讀取病房資料，用來檢查護理紀錄的完整性與一致性
> 格式檢查檔：[patient-daily.schema.json](hospital-data-spec/patient-daily.schema.json)、[manifest.schema.json](hospital-data-spec/manifest.schema.json)（JSON Schema 2020-12）
> 範例資料：專案根目錄 `mock_data/`（完全虛構）

## 1. 稽核項目與所需資料

| 代碼 | 稽核項目 | 需要的資料區塊 |
|---|---|---|
| R01 | 入院經過 ↔ 身體評估一致性 | `admission_assessment`、`daily_physical_assessments` |
| R02 | 前後紀錄 Copy／一成不變／時效 | `nursing_progress_notes`、`vital_signs`、`lab_results`、`tubes` |
| R03 | 入院護理評估指定項目完整性 | `admission_assessment` |
| R04 | 每日身體評估異常是否有後續追蹤 | `daily_physical_assessments`、`nursing_progress_notes` |
| R05 | 轉入／轉出摘要完整性 | `transfers`、`nursing_progress_notes`、`tubes` |
| R06 | 會診資訊 ↔ 護理紀錄 | `consultations`、`nursing_progress_notes` |
| R07 | 給藥後療效／副作用／不良反應追蹤 | `medication_orders`、`nursing_progress_notes`、`lab_results` |

本系統**只讀取、不回寫**任何院內資料。

## 2. 交付方式

### 2.1 目錄與檔名

```
<交付根目錄>/
├── 20260901/                 # 業務日期 YYYYMMDD
│   ├── manifest.json         # 當天資料包清單
│   ├── A病患.json            # 一位病患一個檔，檔名 = patient_id + .json
│   └── B病患.json
└── 20260902/
    └── …
```

- 一個病房一個交付根目錄（例如 W51 一個、W53 一個）。
- 每天 **01:00** 產出**前一天**（業務日期）的資料包；本系統約 03:00 讀取。
- 業務日期：Asia/Taipei 時區 00:00:00–23:59:59。
- 當天在該病房出現過的病患（含當天入院、轉入、轉出、出院）都要有檔案；轉出或出院後的隔天起就不再出現。
- 編碼 **UTF-8**（不含 BOM）；檔案內容為單一 JSON 物件。

### 2.2 增量規則

- 每天只放**當天新增或修改**的紀錄；本系統會自己累積歷史資料，做前幾天的比對。
- 判斷「當天」的依據：紀錄時間（`recorded_at`、`assessed_at`…）在當天，或修改時間（`last_modified_at`）在當天。
- 紀錄被修改：用**同一個** ID 再送一次完整內容，並填 `last_modified_at`；本系統以 ID 覆蓋。
- 會診：開立、簽收、回覆任一狀態改變的那天，都送一次該筆會診的最新完整狀態。
- 管路（`tubes`）：每天送**當天的現況清單**（當天仍留置，或當天移除的管路）。
- `patient` 每天都要有（當天的床號、狀態）。
- 紀錄被刪除：v0.1.0 尚未定義，請院方告知院內刪除方式後再補（見第 6 節）。

### 2.3 時間格式

- 時間一律 ISO 8601 並帶時區：`2026-09-01T10:30:00+08:00`
- 日期：`2026-09-01`

### 2.4 去識別化

- **不提供**：姓名、病歷號、身分證字號、生日、電話、地址。
- 病患用院方自訂的去識別代碼 `patient_id`（例：`ABC001`），同一人每天固定。
- 人員（護理師、醫師、營養師）一律用院方人員代碼（例：`N103`、`D201`），不放姓名。
- 紀錄內文若含人名（例如貼上的「○○○營養師會診」），請在產出時以人員代碼或「醫師」「營養師」等職稱取代。

### 2.5 命名與值的原則

- 欄位名稱：英文 snake_case（如下表）。
- 臨床選項的值：**照院內畫面原文**（例：`"正常"`、`"不易入睡"`、`"痰音"`）。
- 系統代碼：英文（例：`shift: "day"`、`direction: "in"`）。
- 畫面上空白（未填）的項目：用 `null`，不要省略欄位。
- 沒有資料的清單：用空陣列 `[]`。

## 3. manifest.json

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `schema_version` | string | ✅ | 固定 `"0.1.0"` |
| `ward_code` | string | ✅ | 病房代碼，例 `W51` |
| `ward_name` | string | ✅ | 例 `內科病房` |
| `business_date` | date | ✅ | 業務日期 |
| `generated_at` | datetime | ✅ | 資料包產出時間 |
| `patient_count` | integer | ✅ | 病患檔數 |
| `patients[]` | array | ✅ | 每位病患：`patient_id`、`file`、`bed_code`、`status` |

## 4. 病患檔（patient-daily）

### 4.1 頂層

| 欄位 | 型別 | 必填 | 說明 |
|---|---|---|---|
| `schema_version` | string | ✅ | 固定 `"0.1.0"` |
| `business_date` | date | ✅ | 業務日期 |
| `ward` | object | ✅ | `ward_code`、`ward_name` |
| `patient` | object | ✅ | 4.2 |
| `admission_assessment` | object／null | ✅ | 4.3；只有入院評估建立或修改的那天才有，其他天為 `null` |
| `daily_physical_assessments` | array | ✅ | 4.4 |
| `nursing_progress_notes` | array | ✅ | 4.5 |
| `transfers` | array | ✅ | 4.6 |
| `consultations` | array | ✅ | 4.7 |
| `medication_orders` | array | ✅ | 4.8 |
| `vital_signs` | array | ✅ | 4.9 |
| `lab_results` | array | ✅ | 4.10 |
| `tubes` | array | ✅ | 4.11 |
| `examinations` | array | 選填 | 4.12（候選稽核項目用） |
| `health_educations` | array | 選填 | 4.13（候選稽核項目用） |
| `consent_forms` | array | 選填 | 4.14（候選稽核項目用） |
| `emotional_distress_assessments` | array | 選填 | 4.15（候選稽核項目用） |

### 4.2 patient（病人基本資料）

| 欄位 | 型別 | 說明 |
|---|---|---|
| `patient_id` | string | 去識別病患代碼，跨日固定 |
| `admission_id` | string | 住院序號；同一人再次住院時不同 |
| `bed_code` | string | 當天床號，例 `W51-1` |
| `sex` | `M`／`F` | |
| `age_years` | integer | 年齡（不提供生日） |
| `admission_at` | datetime | 入院時間 |
| `admission_source` | `急診`／`門診`／`轉院`／`其他` | |
| `admission_diagnosis` | string | 入院診斷 |
| `attending_physician_id` | string | 主治醫師代碼 |
| `status` | `inpatient`／`transferred_out`／`discharged` | 當天結束時的狀態 |
| `status_changed_at` | datetime／null | 轉出或出院時間 |

### 4.3 admission_assessment（入院護理評估）

對應畫面：入院評估。`sections` 下固定 8 個區塊，每個區塊都有 `completed`（是否完成）與 `content`（內容）。

| 區塊 | 稽核方式 | `content` 建議內容 |
|---|---|---|
| `basic_info` 基本資料 | 有無 | 教育程度、語言、宗教、婚姻、主要照顧者、入院方式… |
| `personal_history` 個人病史 | 有無 | `past_history[]`（疾病、發生西元年）、手術史、過敏、血型、菸酒 |
| `nutrition` 營養評估 | 有無 | 身高、體重、BMI、飲食、營養篩檢分數 |
| `daily_living` 日常生活型態 | 有無 | ADL、排便、睡眠…（兒科不適用） |
| `physical_assessment` 身體評估 | **內容完整性** | `narrative`（文字描述）＋`items`（同 4.4 的 `items` 結構） |
| `psychosocial` 心靈社會 | 有無 | 情緒、因應方式、支持系統… |
| `admission_course` 住院經過 | **內容完整性** | `text`：全文（應含發生時間、不適症狀、就醫經過、處理、住院原因） |
| `environment` 環境 | 有無 | `introduced_items[]`（已介紹項目）、`not_introduced[]`（未介紹項目＋原因） |

其他欄位：`record_id`、`assessed_at`、`author_id`、`last_modified_at`。

### 4.4 daily_physical_assessments（每日身體評估）

對應畫面：身評。**所有項目都要送**（正常與異常都要），本系統自行判斷異常。一個班一筆。

| 欄位 | 說明 |
|---|---|
| `record_id`、`assessed_at`、`author_id`、`last_modified_at` | |
| `shift` | `day`（白班）／`evening`（小夜）／`night`（大夜） |
| `items` | 下表 |

`items` 各項目（值照院內畫面選項原文；空白為 `null`）：

| 欄位 | 畫面項目 | 值 |
|---|---|---|
| `consciousness` | 意識 | `{measured_at, scale: "GCS"/"RASS", e, v, m, rass}`；插管時 V 填 `"T"` |
| `pain` | 疼痛分數 | `{scale: "10分法", score: 0–10, unable_to_assess}` |
| `sleep` | 睡眠 | 正常／不易入睡／早醒／淺眠／嗜睡／無法評估 |
| `airway` | 氣管 | 無／氣管內管／氣切 |
| `tubes` | 管路 | `{has_tube, description}`（畫面上的管路文字） |
| `pulse` | 脈搏 | `{status: 正常/異常, abnormal_types: [不規律, 快, 慢]}` |
| `limb_circulation` | 肢體循環 | 微血管快速填滿／微血管延遲填滿(大於五秒)／輕微水腫(無壓窩)／中、重度水腫(有壓窩) |
| `breath_sounds` | 呼吸音 | `{status, abnormal_types: [痰音, 哮喘音, 濕囉音], other}` |
| `cough`、`sore_throat` | 咳嗽、喉嚨痛 | 無／有／無法評估 |
| `bowel_sounds` | 腸音 | 正常／過快／過慢／無腸音 |
| `appetite` | 食慾（可複選） | [正常, 減少, 灌食, NPO, 嘔吐] |
| `urination` | 泌尿 | `{status, abnormal_types: [頻尿, 尿失禁, …, 其他], other}` |
| `skin_pressure_prone_sites` | 皮膚：容易壓紅部位（可複選） | [薦骨, 坐骨, 股骨粗隆, 足部, 頭頸部, 面部, 軀幹, 上下肢, 無] |
| `muscle_power` | 肌肉力量 | `{left_upper, right_upper, left_lower, right_lower}`：5–0／無法評估／鎮靜劑使用 |
| `mobility` | 移動能力 | 完全能動／尚可自行翻身／無法自行翻身／不能動 |
| `fall_risk` | 跌倒危險 | `{unable_to_move, risk_factors[], medications[], score, high_risk, osteoporosis_high_risk}` |

### 4.5 nursing_progress_notes（護理過程紀錄）

對應畫面：過程紀錄 → 護理紀錄。

| 欄位 | 說明 |
|---|---|
| `record_id` | 紀錄 ID |
| `recorded_at` | 紀錄時間（畫面標題列的時間） |
| `title_category` | 標籤：健康問題／交班／導管照護／會診／營養照會建議／轉出摘要／轉入摘要／入院護理／出院護理／護理指導／其他 |
| `title` | 畫面標題列全文，例 `健康問題 ：組織灌流改變：心肺、周邊血管` |
| `content` | 內文全文 |
| `author_id` | 建立者代碼 |
| `last_modified_at` | 最後修改時間；未修改為 `null` |
| `has_image` | 內文是否貼有圖（例如心電圖）；圖本身不用傳 |

- 轉出／轉入摘要過長而拆成多筆（以「(續)」接續）時，**照原樣分筆送**即可。
- R06 以標籤比對：醫師會診對應 `會診`，營養師照會對應 `營養照會建議`。

### 4.6 transfers（轉入／轉出）

`transfer_id`、`direction`（`in`／`out`）、`occurred_at`、`from_unit`、`to_unit`、`reason`。

### 4.7 consultations（會診）

對應畫面：病歷 → 本次會診清單；營養師照會也放這裡。

| 欄位 | 說明 |
|---|---|
| `consultation_id` | 會診 ID |
| `consultant_role` | `醫師`／`營養師` |
| `department` | 會診科別，例 `心臟外科`、`營養室` |
| `consult_type` | `REGULAR`／`URGENT` |
| `ordered_at`、`requested_by` | 開立時間、開立者 |
| `signed_at`、`signed_by` | 簽收時間、簽收者 |
| `replied_at` | 醫師（營養師）書寫紀錄時間＝回覆時間 |
| `status` | `未簽收`／`已簽收`／`已回覆` |
| `condition_summary` | 病況簡述 |
| `reply_content` | 回覆內容（營養師為訪視紀錄全文） |

本系統以 `replied_at` 起算，檢查護理紀錄是否在「回覆當天到隔天」內有對應標籤的紀錄。

### 4.8 medication_orders（藥囑與給藥）

對應畫面：醫藥囑 → 臨時藥囑／高警訊用藥追蹤。**第一版只需送：高警訊用藥（含常規）＋臨時藥囑（STAT、PRN）**；其他常規藥囑選填。

| 欄位 | 說明 |
|---|---|
| `order_id` | 藥囑 ID（跨日固定） |
| `order_category` | `常規`／`臨時` |
| `drug_name` | 藥囑名稱，例 `Morphine HCl Inj 10mg/1ml` |
| `route`、`dose`、`unit`、`frequency` | 途徑（IVP、IVA、SC、PO…）、劑量、單位、頻次（STAT、Q8H…） |
| `is_high_alert` | 是否為院內高警訊用藥 |
| `ordered_at`、`prescriber_id` | 開立時間、開立醫師 |
| `status` | `未執行`／`執行中`／`已執行`／`到期停用`／`DC` |
| `administrations[]` | 當天的給藥執行：`administration_id`、`administered_at`、`administered_by`、`dose`、`unit`、`rate`（幫浦速率）、`status`、`remark` |

### 4.9 vital_signs（生命徵象）

`record_id`、`measured_at`、`body_temperature`、`temperature_site`（耳溫／口溫／腋溫／肛溫）、`pulse`、`respiration`、`sbp`、`dbp`、`spo2`、`oxygen_therapy`（例 `room air`、`鼻導管 3L/min`）、`measured_by`。

### 4.10 lab_results（檢驗結果）

`record_id`、`order_name`、`item`、`value`（字串，照報告原值）、`unit`、`reference_range`、`abnormal_flag`（`H`／`L`／`null`）、`collected_at`、`reported_at`。

### 4.11 tubes（管路）

對應畫面：建立管路資料。`tube_id`、`tube_type`（IV、Foley、NG、CVC、A-V shunt…）、`site`、`size`、`inserted_on`（不詳用 `null`）、`removed_on`、`fixation`、`appearance`。

### 4.12–4.15 選填區塊（候選稽核項目）

| 區塊 | 欄位 |
|---|---|
| `examinations` 檢查醫囑（病歷 → 本次醫囑清單） | `order_id`、`order_name`、`ordered_at`、`performed_at`、`status`（已開立／已執行／正式報告／取消）、`is_invasive`、`report_summary` |
| `health_educations` 護理指導 | `record_id`、`recorded_at`、`topic`、`target`（病人／家屬／病人及家屬）、`content`、`author_id` |
| `consent_forms` 同意書 | `consent_id`、`form_name`、`related_order_id`、`status`（待簽／已簽／拒簽）、`signed_at` |
| `emotional_distress_assessments` 情緒困擾 | `record_id`、`assessed_at`、`score`（0–10）、`suicidal_ideation`、`author_id` |

## 5. 精簡範例

```json
{
  "schema_version": "0.1.0",
  "business_date": "2026-09-03",
  "ward": { "ward_code": "W51", "ward_name": "內科病房" },
  "patient": {
    "patient_id": "ABC001", "admission_id": "ADM-ABC001-01", "bed_code": "W51-1",
    "sex": "M", "age_years": 72, "admission_at": "2026-09-01T10:30:00+08:00",
    "admission_source": "急診", "admission_diagnosis": "NSTEMI",
    "attending_physician_id": "D201", "status": "inpatient", "status_changed_at": null
  },
  "admission_assessment": null,
  "daily_physical_assessments": [ { "record_id": "…", "shift": "day", "items": { "sleep": "正常", "…": "…" } } ],
  "nursing_progress_notes": [
    {
      "record_id": "NPN-0001", "recorded_at": "2026-09-03T14:20:00+08:00",
      "title_category": "會診", "title": "會診", "content": "【會診】…",
      "author_id": "N103", "last_modified_at": null, "has_image": false
    }
  ],
  "transfers": [], "consultations": [], "medication_orders": [],
  "vital_signs": [], "lab_results": [], "tubes": []
}
```

完整範例見 `mock_data/`。

## 6. 待院方確認事項

1. **高警訊用藥清單**：院內定義的品項，以及 `is_high_alert` 能否由系統直接帶出。
2. **紀錄標籤清單**：過程紀錄標題列的完整分類（目前已知：健康問題、交班、導管照護、會診、營養照會建議、轉出摘要、轉入摘要），以及營養師照會、醫師會診的標籤是否固定。
3. **長摘要分筆**：轉出／轉入摘要拆成多筆時，能否合併成一筆送；不能也沒關係，本系統會依「(續)」合併。
4. **會診範圍**：是否只送醫師會診與營養師照會；其他團隊（復健、社工、心理師）是否一併提供。
5. **修改與刪除**：紀錄修改後能否帶出 `last_modified_at`；刪除的紀錄要怎麼表示。
6. **身評空白**：畫面空白（未評估）的項目能否以 `null` 送出，與「正常」區分。
7. **交付方式**：中繼站位置、傳輸方式、認證方式、保留天數。

## 7. 版本紀錄

| 版本 | 日期 | 說明 |
|---|---|---|
| 0.1.0 | 2026-10-01 | 初版，依 0911、0916、0924 討論與院內畫面整理 |
