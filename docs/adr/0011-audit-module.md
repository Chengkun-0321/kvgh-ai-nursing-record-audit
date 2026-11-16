# ADR 0011：稽核模組架構（七項一律經 LLM、統一流程、稽核週期與執行狀態）

- 狀態：採用
- 日期：2026-11-16

## 背景

- 院方的 7 項稽核（R01–R07，來源見 [audit-rules.md](../conventions/audit-rules.md)）需要的流程是：系統整理院方資料 → 每項稽核專屬的 prompt → LLM 回傳 JSON → 程式驗證 → 存入資料庫 → 病患頁顯示。由使用者手動觸發。
- 設計目標有三個：
  - 獨立：每項稽核自己管理資料需求、prompt、輸出驗證。
  - 共用：流程、LLM 呼叫、Evidence 核對、持久化只寫一次。
  - 可擴充：新增第 8 項不需要改主流程。
- 既有文件的「Rule 優先，LLM 其次」與 `engine`（`rule`／`llm`／`hybrid`）區分，這一版不採用：
  - 專案負責人決定七項走同一套流程（整理資料 → LLM → 驗證 → 儲存），讓新增稽核項目時不必分辨引擎、不改主流程。
  - 院方資料沒有身評的異常標記（R04）、沒有選項清單（R01）、沒有回覆狀態（R06），程式能獨立判定的部分本來就少。
  - 代價：R03（工作清單只有「有填寫／沒有填寫」）本來可由程式直接判定，改經 LLM 後多一次呼叫與不確定性；以 `validate_output` 與 Evidence 核對把關。
- 院方資料的日期結構也與 [ADR 0010](0010-hospital-raw-data-viewer.md) 的描述不完全相同，見決策 5。

## 決策

### 1. 七項稽核一律經 LLM 判定

- 程式只負責三件事：整理事實（`AuditInput`）、核對 Evidence、驗證 LLM 輸出的結構與規則專屬的約束。程式不下判定。
- LLM 只能回傳 `PASS`、`WARNING`、`NEEDS_REVIEW`（`LlmVerdict`）。`ERROR` 這一版不會產生。
- `WARNING` 必須至少有一筆通過原文核對的 Evidence；否則降為 `NEEDS_REVIEW`，絕不因此視為 `PASS`。
- 取代的既有說法：
  - [CLAUDE.md](../../CLAUDE.md) 核心原則 4「Rule 優先，LLM 其次」。
  - [audit-rules.md](../conventions/audit-rules.md) 規則清單的 `engine` 欄，以及 `Engine` 列舉與舊的 `AuditRule` 介面（`applies_to`／`evaluate`）。

### 2. 統一流程，規則可替換

`AuditService.run_rule` 的固定流程（實際順序以 `services/audit/service.py` 為準）：

```
build_audit_context             共用：讀取院方資料（不入庫）
 → rule.check_availability      規則：可稽核／當日無此事件／院方未提供資料
 → rule.build_input             規則：整理送給 LLM 的變數與可引用的紀錄
 → gateway.complete_structured  共用：渲染 prompt、呼叫模型、JSON 驗證與格式重試
 → rule.validate_output         規則：規則專屬的輸出驗證
 → verify_output                共用：Evidence 核對、WARNING 降級、整體判定
 → audit_run_crud.add           共用：寫入 audit_runs、audit_findings
```

- 不適用或資料未提供時，在第 2 步結束，照樣寫一筆紀錄，不呼叫 LLM。
- 規則是純函式：不碰 DB、不呼叫 LLM、無副作用。
- 新增第 8 項＝新增 `rules/rNN_<name>.py`＋`prompts/rNN_<name>/v1.j2`＋`registry.py` 一行。流程不變。

### 3. 稽核週期

| 週期（`AuditCycle`） | 規則 | 稽核日期（`effective_business_date`） | 在其他日期的呈現 |
|---|---|---|---|
| `once_per_admission` 一次性 | R01、R03 | 固定為入院日（院方入院時間的日期）；院方沒有入院時間時用畫面所選日期 | 每一天都顯示同一筆結果；任何一天都能執行或重跑 |
| `daily` 每日 | R02、R04 | 畫面所選日期 | 各日各自一筆 |
| `event` 事件 | R05、R06、R07 | 畫面所選日期（事件發生日） | 當日無事件則顯示「當日無此事件」 |

- 一次性規則的理由：入院評估是快照，每天的檔案都會帶著；`data/` 目前只有 2 天，多數病人在 11/04 之前已入院，若限定只能在入院日當天稽核，可稽核的病人會很少。
- 一鍵稽核：一次性規則已有完成的結果時不重跑（`include_in_run_all` 為 false），要重跑按該項自己的按鈕。

### 4. 執行狀態與重跑

| 狀態（`AuditRunStatus`） | 何時產生 | 是否呼叫 LLM | `verdict` |
|---|---|---|---|
| `COMPLETED` | LLM 輸出通過驗證；或 LLM 輸出未通過格式與規則驗證（此時 `verdict` 為 `NEEDS_REVIEW`，`status_reason` 說明原因） | 是 | 有值 |
| `NOT_APPLICABLE` | 當日無此事件（例如 R04 當日沒有身評） | 否 | 無 |
| `DATA_UNAVAILABLE` | 院方沒有提供所需資料，或規則為預留（R05、R07） | 否 | 無 |
| `FAILED` | 連線、額度等 `AppError`，或未預期的例外 | 視情況 | 無；訊息為固定文字，不含病歷內容 |

- 缺少使用中的模型設定時，API 回 409，**不寫入紀錄**。
- 重跑不覆蓋：每次執行新增一列 `audit_runs`；畫面與總覽顯示同一組條件（病患、規則、稽核日）下 `created_at` 最新的一列。

### 5. 資料歸日（修正 ADR 0010 的一項描述）

- 稽核的歸日一律依紀錄本身的時間（`event_day`，Asia/Taipei），不依院方資料夾的日期。
- 理由，已用院方資料驗證（2026-11-16，以程式統計 W63 2026-11-04 的 41 份病人檔，未修改資料）：
  - 11/04 的檔案中，有 23 份的每日身體評估日期為 11/05。
  - 因此「每日檔只含當日紀錄」（ADR 0010 第一張表）對每日身評不成立。
  - 轉床資料同樣是最新一筆：有 1 份 11/04 的檔案，轉床的操作日期是 11/05。GCS 也是最新一筆，測量時間都早於檔案日期（2026-09-24 至 10-30）。
- ADR 0010 的其他決策不變；該檔已加註記指向本 ADR。
- 院方資料沒有紀錄時間時，歸日退回資料夾日期（`event_day` 的 fallback）。

### 6. record_id 的來源

- 院方資料沒有紀錄 ID。Evidence 的 `record_id` 使用時間軸的 `event_id`（內容雜湊，不含資料日期）。相同內容跨日會得到相同 ID。
- 工作清單是程式組出來的紀錄，`record_id` 為 `work_checklist-<內容雜湊前 16 碼>`。
- Evidence 的來源、欄位、日期、時間由程式依 `record_id` 回填，不採用 LLM 給的值。

### 7. 觸發方式

- 這一版只有手動觸發：
  - 病患頁每項規則的按鈕。
  - 一鍵稽核：前端對 `include_in_run_all` 為真的規則各發一次 `POST`。
- 不在這一版：排程、整個病房的批次稽核。病床總覽改讀稽核結果已完成，見決策 8。
- 規劃中的批次入口 `run_daily_audit` 尚未實作，不存在於程式碼中。

### 8. 病床總覽讀取稽核結果

- 每床的狀態由該床各規則「最新一次且為 `COMPLETED`」的結果算出；取最嚴重的判定（嚴重度排序與整體判定共用 `services/audit/severity.py`）。沒有任何已完成結果時為「尚未稽核」。
- 進度：可稽核的規則（`check_availability` 為可執行，與病患頁 `can_run` 同一判斷）中，最新一次為 `COMPLETED` 的數量。最新一次為 `FAILED` 不算已稽核。
- 稽核日、可否稽核、最新結果的查詢與病患頁使用同一組函式（`service.rule_day_on`、`context_from_history`、`crud.audit_run.list_latest_runs`），不另算。一次性規則以入院日查詢，計入查詢當日的病床總覽。
- 查詢以一次批次完成（視窗函式 `ROW_NUMBER`，SQLite 與 PostgreSQL 皆可），不逐床、逐規則查詢。
- 已知差異：病床總覽的狀態只計「已完成」結果，不要求該規則當日仍可稽核；病患頁的進度則要求可稽核。目前院方資料下兩者一致（已以 W63 全部 41 床核對）。

## 影響

- 好處：
  - 每項規則的範圍清楚；LLM 與程式的界線清楚（判定與核對分開）。
  - 結果可重現：每列記錄 `model`、`prompt_version`、`system_prompt_version`、`input_digest`（渲染後 prompt 的 sha256，不存全文）。
  - 新增規則的改動範圍限定在規則模組、prompt 與 registry。
- 代價：
  - 七項稽核都依賴使用中的模型設定，沒有設定時無法稽核。
  - 格式不符與驗證失敗會增加 `NEEDS_REVIEW` 的數量，護理長需要逐項確認。
  - 每次手動執行都會產生模型費用（一鍵稽核會同時發出多個請求，上限由 `LLM_MAX_CONCURRENCY` 控制）。
- 後續（另案，不在本 ADR 範圍）：
  - 排程與批次入口。
  - 病床總覽改讀 `audit_runs`：已完成（決策 8）。
  - 準確率評估（golden set），目前 `backend/evaluation/` 尚未建立。
- 待確認（不自行假設，需要院方或護理長決定）：
  - R06 的追蹤期限算法：目前以會診日期起算，期限為當日到當日加 `AUDIT_CONSULT_FOLLOWUP_DAYS`（暫定 1 日，含當日）。院方沒有會診的簽收與回覆時間。
  - R04 是否把「跌倒危險」「移動能力」視為需要追蹤的異常項目。目前程式沒有排除，但 [audit-rules.md](../conventions/audit-rules.md) 原本把「防跌」列為明確排除項目。
  - R05、R07 所需的院方資料：轉出／轉入摘要、給藥執行紀錄（執行時間、執行者）。
  - R01、R03 的選項清單與「不適用」狀態。
  - 一次性規則的重新稽核：院方沒有入院評估的修改時間，修改後以手動重跑處理。
