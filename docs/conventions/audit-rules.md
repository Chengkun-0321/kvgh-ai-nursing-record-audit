# 稽核規則規範

來源：專案外部文件 `高榮護理師workflow/20260916高榮護理師需求確認/依據9:11稽核項目需求確認.md`（護理長 9/11 稽核討論 PDF 整理）。
**只實作本清單內的規則；清單變更需先與護理長確認，再更新本文件。**

流程、稽核週期、執行狀態的決策見 [ADR 0011](../adr/0011-audit-module.md)。本文件描述各規則的內容與程式介面。

## 規則清單

| 代碼 | 稽核項目 | 稽核週期 | 狀態 |
|---|---|---|---|
| R01 | 入院經過 ↔ 身體評估一致性 | 一次性 | 已實作 |
| R02 | 近幾日紀錄複製／一成不變／時效性 | 每日 | 已實作 |
| R03 | 入院護理評估指定項目完整性 | 一次性 | 已實作 |
| R04 | 每日身體評估異常 ↔ 後續追蹤紀錄 | 每日 | 已實作 |
| R05 | 轉入／轉出摘要完整性 | 事件 | 預留（模組與 prompt 已建，不呼叫 LLM） |
| R06 | 會診資訊 ↔ 護理紀錄 | 事件（截至稽核日逐筆追蹤，見 ADR 0012） | 已實作 |
| R07 | 給藥後療效／副作用／不良反應追蹤 | 事件 | 預留（模組與 prompt 已建，不呼叫 LLM） |
| R08 | 侵入性檢查／治療前說明 | — | 候選（高度可行），未實作 |
| R09 | 藥物執行前衛教 | — | 候選（高度可行），未實作 |
| R10 | 情緒困擾 ≥ 4 後續處置紀錄 | — | 候選（待確認），未實作 |
| R11 | 待簽同意書提醒 | — | 候選（報表附加項），未實作 |

- 稽核週期的定義與日期規則見 ADR 0011 決策 3；其中一次性規則的重跑與 R06 的追蹤範圍已由 ADR 0012 修正。
- **稽核日必須已結束**（全部七項）：稽核日 < 今天（Asia/Taipei）才可執行。所選日期未結束時，可稽核性為 `DAY_NOT_ENDED`，`run_rule` 回 409，不寫入紀錄（ADR 0012 決策 1）。
- **一次性規則完成後不可再執行**（R01、R03）：最新一列為 `COMPLETED` 且非驗證失敗時，`can_run` 與 `include_in_run_all` 為 false，`run_rule` 回 409，不寫入紀錄。驗證失敗造成的 `NEEDS_REVIEW` 仍可重跑（ADR 0012 決策 3）。
- **寬限期中**（R06）：逐筆會診尚未到期且未見對應紀錄時為 `IN_GRACE`，該筆判定 `PASS`，仍可稽核（ADR 0012 決策 2）。
- **預留**：`check_availability` 固定回傳 `DATA_UNAVAILABLE`，流程不呼叫 LLM。資料到位後的修改步驟寫在各模組的 docstring。
- 候選規則（R08–R11）尚未實作。規劃的開關設定 `ENABLED_AUDIT_RULES` 目前不存在於 `core/config.py`；實作時再新增，並同步 `.env.example`。

### 各規則的必要要素

必要要素寫成該規則模組的常數，由程式注入 prompt，不在 prompt 內重複寫死。

| 代碼 | 必要要素 | 常數位置 |
|---|---|---|
| R01 | 發生時間、不適症狀、就醫經過、處理、住院原因 | `r01_admission_course.REQUIRED_ELEMENTS` |
| R03 | 基本資料、個人病史、營養評估、日常生活型態、身體評估、心靈社會、住院經過、環境 | `r03_admission_completeness.REQUIRED_ITEMS` |
| R05 | 轉出摘要：住院期間重要檢查、治療結果、目前病況、管路、傷口（視病況）、健康問題、轉出原因；轉入摘要：意識、呼吸、身體活動、管路、皮膚狀況、現存健康問題 | `r05_transfer_summary.REQUIRED_ELEMENTS`、`CONDITIONAL_ELEMENTS` |
| R04 | 異常項目是否在護理紀錄中被描述、處置、追蹤 | 判斷準則在 prompt |
| R06 | 會診後的護理紀錄（類別為「會診」「營養照會建議」）是否有相應書寫 | `r06_consultation.FOLLOWUP_CATEGORIES` |
| R07 | 療效、副作用、不良反應時是否通知醫師、處理、通報、紀錄 | `r07_medication_followup.RESPONSE_ELEMENTS` |

## 各規則的內容

以下為已實作與預留規則的程式行為。「LLM 判定」一律指由 LLM 依 prompt 判斷，程式只做 [輸出驗證](#輸出驗證)。

### R01 入院經過 ↔ 身體評估一致性（一次性）

- 執行：一次性。已完成後不可再執行，見 ADR 0012 決策 3。
- 適用條件：有「入院經過」與「入院身體評估」紀錄。缺任一者為 `DATA_UNAVAILABLE`。
- 輸入：入院經過全文、入院身體評估原文（各欄位）、院方入院時間。
- LLM 判定：
  - 五項必要要素是否在入院經過中提及。
  - 入院經過與入院身體評估是否相符。
- 專屬輸出（存入 `details`）：`elements`，每項 `{element, mentioned}`。
- 專屬驗證：
  - `elements` 必須正好涵蓋五項要素，名稱不可增減。
  - 有任一要素未提及時，整體判定不得為 `PASS`。
- 顯示文字：未提及的要素仍記為 `NEEDS_REVIEW`，但該筆發現顯示「未見紀錄」而非「無法判定」（模型已判定「未提及」，不是判斷不了）。只改顯示，不改判定分級；由規則的選用介面 `finding_labels` 提供，在 `views.to_run_read` 套用。
- 已知限制：院方沒有選項清單，身評「沒有提到」某項不代表正常或異常，因此不據此判為不一致。

### R02 紀錄複製／一成不變／時效性（每日）

- 適用條件：當日有護理過程紀錄。沒有則 `NOT_APPLICABLE`。
- 回溯期間：`AUDIT_COPY_LOOKBACK_DAYS`（預設 5，含當日；即當日加前 4 日）。資料不足時有幾天用幾天。
- 程式整理的輸入：
  - 回溯期間內的護理紀錄，依類別排列，同類別的前幾日與當日相鄰。
  - 回溯期間內的生命徵象。
  - 院方標記為異常的檢驗結果（只列標記項目，未標記的不列）。
  - 身體評估的「管路」欄位（只列管路欄）。
  - 程式計算的各類別相似度，**只作參考值**，不設門檻，存入 `details.similarities`。
- 相似度：每個當日類別，與最近一個前日同類別紀錄比對（去除「類別」欄位後的內文，正規化後以字元為單位計算 `difflib` 比率，取兩位小數）。任一方為空或前日沒有同類別紀錄時為空值。
- LLM 判定：
  - 當日紀錄是否與前幾日同類別紀錄幾乎相同。
  - 內文引用的生命徵象是否為當日的值。
  - 紀錄與前幾日相似，但生命徵象、檢驗、管路已變化時，紀錄是否反映變化。
- 專屬輸出：`category_judgements`，每類別 `{category, judgement}`，`judgement` 為「幾乎相同」「有實質差異」「無法判斷」。
- 專屬驗證：
  - `findings` 的 `item` 必須是當日護理紀錄的類別，或「生命徵象」「檢驗」「管路」之一。
  - `category_judgements` 的類別必須是當日有紀錄的類別。
  - 前日沒有同類別紀錄的類別，只能判為「無法判斷」。
- 規則：固定格式類別（例如譫妄評估、約束護理過程、壓傷（預防）計畫及護理）不因格式相同判為複製，寫在 prompt。
- 已知限制：護理紀錄沒有時分；回溯資料可能只有 2 天。

### R03 入院護理評估完整性（一次性）

- 執行：一次性。已完成後不可再執行，見 ADR 0012 決策 3。
- 適用條件：院方有工作清單。沒有則 `DATA_UNAVAILABLE`。
- 輸入：工作清單 7 項的填寫狀態（合成為一筆 `work_checklist` 紀錄）、入院經過紀錄是否有內容。
- 必要項目與院方欄位的對照：

  | PDF 項目（輸出用名稱） | 院方工作清單欄位 |
  |---|---|
  | 基本資料 | 基本資料 |
  | 個人病史 | 個人病史 |
  | 營養評估 | 營養評估 |
  | 日常生活型態 | 日常生活 |
  | 身體評估 | 身體評估 |
  | 心靈社會 | 心理評估 |
  | 住院經過 | （無；以入院經過紀錄是否有內容判斷） |
  | 環境 | 環境 |

- LLM 判定：哪些必要項目未完成。
- 專屬輸出：`incomplete_items`。
- 專屬驗證：`findings` 的項目與 `incomplete_items` 都必須是上表的 PDF 項目名稱。
- 已知限制：院方工作清單只有「有填寫」與「沒有填寫」，沒有「不適用」狀態。

### R04 身評異常追蹤（每日）

- 適用條件：當日有每日身體評估。沒有則 `NOT_APPLICABLE`。
- 輸入：
  - 當日身評的全部欄位原文（欄位名稱去重後列為項目清單）。
  - 當日全部護理過程紀錄。沒有時 prompt 寫明「資料中未見紀錄不代表未書寫」，所有可能的異常項目判為 `UNCERTAIN`。
  - 輔助資料（只當背景）：當日生命徵象、會診、用藥。
- LLM 判定：每個異常或無法確定是否異常的項目，狀態為：
  - `FOUND`：異常，且當日護理紀錄有相應書寫。
  - `NOT_FOUND`：異常，但未見相應書寫。
  - `UNCERTAIN`：無法確定身評是否異常，或無法確定護理紀錄是否相應。
- 院方沒有標示異常項目，異常判斷依 prompt 中的準則由 LLM 做。
- 專屬輸出：`flagged_items`，每項 `{item, status, reason}`。
- 專屬驗證（`r04_checks.py`）：
  - `flagged_items` 的項目必須是當日身評欄位名稱，且不重複。
  - `NOT_FOUND` 的 finding 必須是 `WARNING`；`UNCERTAIN` 必須是 `NEEDS_REVIEW`。
  - `FOUND` 的項目可以不列；若列出，只能是 `PASS`。
  - `NOT_FOUND`、`UNCERTAIN` 的依據必須指向當日身評紀錄，不得引用護理紀錄或輔助資料。
  - `summary` 與 finding 的 `message` 不得含「寫錯」「漏寫」「違規」「忘記」。
- 已知限制：「當日沒有護理紀錄時全部判為 `UNCERTAIN`」只寫在 prompt，程式沒有強制驗證。

### R05 轉入／轉出摘要完整性（事件，預留）

- 狀態：`check_availability` 固定回傳 `DATA_UNAVAILABLE`，原因為「院方資料沒有轉出摘要、轉入摘要，轉床紀錄只有病房內換床」。不呼叫 LLM。
- 模組與 prompt 已依預期的資料形狀實作並有測試（以虛構資料）；資料到位後的修改步驟見 `r05_transfer_summary.py` 的 docstring。
- 限制：`check_availability` 尚未依院方資料判斷，因此預留狀態不會因資料到齊而改變，需先修改。

### R06 會診資訊 ↔ 護理紀錄（事件）

- 稽核日 D 為所選日期，結果記在 D。追蹤範圍為 D−N 至 D（含），N 為 `AUDIT_CONSULT_FOLLOWUP_DAYS`，預設 1 日，待院方確認。
- 每筆會診的追蹤期限為會診日 C 至 C＋N（含）；C＋N 是期限到期日。
- 已結束的稽核日，範圍內有會診即 `available`；沒有則為 `not_applicable`，原因「追蹤範圍內沒有會診」。
- 輸入：追蹤範圍內的每筆會診，及同期類別為「會診」或「營養照會建議」的護理紀錄。資料不超過 D。
- 程式逐筆計算到期日、是否到期與資料是否到齊。會診日早於病患最早資料日時，標示資料尚未到齊；此檢查不驗證期間內是否有缺日。
- LLM 使用 `r06_consultation/v3.j2`，判斷期限內且不晚於 D 是否已有對應護理紀錄。它只判斷有無，不比對建議內容。prompt 指示以內文日期、時間與醫師區分同科多次會診。

| 逐筆狀態 | 條件 | 判定 | prompt 要求的訊息 |
|---|---|---|---|
| `MATCHED` | 已見期限內對應紀錄 | `PASS` | 已見對應的護理紀錄 |
| `IN_GRACE` | 尚未到期且未見對應紀錄 | `PASS` | 寬限期中，追蹤期限至 ＜到期日＞ |
| `NOT_FOUND` | 已到期、未見紀錄，資料已到齊 | `WARNING` | 期限至 ＜到期日＞，護理紀錄中未見相應紀錄，請確認 |
| `NOT_FOUND` | 已到期、未見紀錄，資料尚未到齊 | `NEEDS_REVIEW` | 期限內的資料尚未提供，暫無法判定 |

- `consultations` 每筆為 `{record_id, item, status}`，與 `findings` 同順序逐筆對應；同日同科不合併。`item` 為會診日及科別，刪除科別中第一個左括號及其後文字；空值用「院方未提供科別」。
- 整體有 `WARNING` 時為 `WARNING`；否則有 `NEEDS_REVIEW` 時為 `NEEDS_REVIEW`；其餘為 `PASS`。只有寬限期中的會診仍為 `PASS`。
- 程式核對會診 ID 完整且不重複、逐筆數量與順序、項目、期限與狀態、資料狀態與判定、整體判定及依據來源。`MATCHED` 依據須為該會診日至到期日內的指定類別護理紀錄；其餘狀態須引用該筆會診。共用 Evidence 核對另驗證原文片段。
- 程式檢查摘要與訊息不得含「寫錯」「漏寫」「違規」「忘記」，但不強制訊息等於 prompt 範例，也不核對語意是否真的對應。LLM 仍負責判斷對應關係。
- 發現標籤：`IN_GRACE` 對應「寬限期中」；`MATCHED` 的預設標籤為「紀錄完整」。細節也顯示 LLM 訊息；prompt 要求「已見對應的護理紀錄」，但程式不強制該字句。規則專屬標籤只取代 `PASS` 與 `NEEDS_REVIEW` 的預設文字。舊結果缺少新狀態欄位時維持預設。
- 顯示限制：標籤以項目名稱對照；同日同科不同會診若狀態不同，寬限期標籤可能套到另一筆 `PASS` 發現。
- 已知限制：院方會診沒有簽收與回覆時間；舊結果查詢未依 prompt 版本過濾。沒有排程，須於所選資料日手動稽核。
- 已驗證案例與未驗證的 `WARNING` 實例見 [ADR 0012](../adr/0012-audit-day-rules.md)。

### R07 給藥後療效與不良反應追蹤（事件，預留）

- 狀態：`check_availability` 固定回傳 `DATA_UNAVAILABLE`，原因為「院方資料只有需要時給藥（PRN）的藥囑，沒有給藥執行時間、執行者、高警訊用藥標記與追蹤紀錄」。不呼叫 LLM。
- 模組與 prompt 已建立。`r07_medication_followup.py` 的 docstring 描述的「當日無此類給藥 → `NOT_APPLICABLE`」尚未啟用。
- 資料到位後的修改步驟見模組 docstring。

## 介面

以下為程式現況（`services/audit/rules/base.py`、`schemas/llm_structured.py`、`core/enums.py`）。

```python
# app/core/enums.py
class Verdict(StrEnum):
    PASS = "PASS"                  # 未發現問題
    WARNING = "WARNING"            # 疑似缺漏／不一致，需人工確認
    ERROR = "ERROR"                # 列舉保留；目前沒有產生來源（LLM 最高只到 WARNING）
    NEEDS_REVIEW = "NEEDS_REVIEW"  # 無法判定（資料不足、輸出未通過驗證）

class AuditCycle(StrEnum):
    ONCE_PER_ADMISSION = "once_per_admission"  # 固定記在入院日
    DAILY = "daily"                            # 畫面所選日期
    EVENT = "event"                            # 畫面所選日期；R06 以追蹤範圍內的會診判斷適用性

class AvailabilityState(StrEnum):
    AVAILABLE = "available"
    NOT_APPLICABLE = "not_applicable"
    DATA_UNAVAILABLE = "data_unavailable"
    DAY_NOT_ENDED = "day_not_ended"            # 所選稽核日尚未結束（今天或之後），不可執行（ADR 0012）

# app/services/audit/rules/base.py
@dataclass(frozen=True)
class Availability:
    state: AvailabilityState
    reason: str | None                 # 繁中說明；可稽核時為 None

@dataclass(frozen=True)
class AuditInput:
    variables: Mapping[str, str]       # prompt 模板變數（字串）
    records: tuple[SourceRecord, ...]  # 本次可被引用的紀錄；Evidence 只能指向這裡的 record_id
    facts: Mapping[str, object]        # 程式算出、要存入 details 的資料（例如 R02 相似度）

class AuditRule(Protocol):
    code: ClassVar[str]                # "R01"
    name: ClassVar[str]                # 顯示名稱
    description: ClassVar[str]         # 在檢查什麼（畫面顯示）
    cycle: ClassVar[AuditCycle]
    prompt_name: ClassVar[str]         # 對應 app/prompts/ 底下的目錄名
    prompt_version: ClassVar[int]      # 對應 v<N>.j2
    output_schema: ClassVar[type[RuleOutput]]

    def check_availability(self, ctx: AuditContext) -> Availability: ...
    def build_input(self, ctx: AuditContext) -> AuditInput: ...
    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None: ...
    # 不符時拋出 LLMOutputError（訊息為模組常數），結果轉為 COMPLETED＋NEEDS_REVIEW

@runtime_checkable
class LabelsFindings(Protocol):  # 選用；僅取代 PASS 或 NEEDS_REVIEW 的顯示文字
    def finding_labels(self, details: Mapping[str, object] | None) -> Mapping[str, str]: ...

# app/schemas/llm_structured.py
LlmVerdict = Literal["PASS", "WARNING", "NEEDS_REVIEW"]

class LlmEvidence(BaseModel):
    record_id: str
    excerpt: str

class LlmFinding(BaseModel):
    item: str
    verdict: LlmVerdict
    message: str
    evidence: list[LlmEvidence]

class RuleOutput(BaseModel):           # 所有規則共同的輸出
    verdict: LlmVerdict
    summary: str
    findings: list[LlmFinding]
    # 規則專屬欄位由子類別加上，存入 details（例：R01 elements、R04 flagged_items、R06 consultations）

# app/services/audit/registry.py
RULE_REGISTRY: dict[str, AuditRule]    # 依代碼排序，畫面依此順序顯示
```

`AuditContext`（`services/audit/context.py`）提供規則所需的資料快照，規則只讀取：

- `records_on(day, source)`、`records_between(start, end, source)`、`records_of(source)`。
- `work_checklist`、`admitted_at`、`admitted_at_text`、`patient_dates`、`business_date`。
- `for_date(day)` 回傳改用另一個稽核日的快照（資料不變）。

## 輸出驗證

處理順序（`services/audit/service.py`）：

1. **格式驗證**（`structured.py`）：LLM 輸出必須是符合 `output_schema` 的 JSON。不符時把錯誤位置與類型附在對話中重試，次數為 `LLM_MAX_RETRIES`。仍不符則 `LLMOutputError`。
2. **規則專屬驗證**（`rule.validate_output`）：見上節各規則的「專屬驗證」。不符則 `LLMOutputError`。
3. **Evidence 核對與整體判定**（`evidence.py`）：見下節。

第 1、2 步的 `LLMOutputError` 都轉為 `COMPLETED`＋`NEEDS_REVIEW`，`status_reason` 為模組常數訊息，不含病歷內容，**絕不視為 `PASS`**。

### Evidence 核對

- LLM 只提供 `record_id` 與 `excerpt`。來源、欄位、日期、時間由程式依 `record_id` 回填。
- 核對方式（`evidence.py`、`text.py`）：
  - `excerpt` 與欄位值都先去除所有空白、格式字元、私用區字元與變體選擇器（院方原文含 U+E01B5 等字元）。
  - 只要 `excerpt` 出現在該紀錄的某個欄位值，或「標籤：值」「標籤值」，即為有效。
  - 跨欄位的片段，比對整筆原文與時間字串。
  - 找不到的 Evidence 丟棄，不影響其他 Evidence。
- `WARNING` 的 finding 沒有任何有效 Evidence 時，該 finding 降為 `NEEDS_REVIEW`。
- 整體判定 = LLM 的整體判定與各 finding 判定中較嚴重者（順序：`PASS` < `NEEDS_REVIEW` < `WARNING` < `ERROR`）。整體為 `WARNING` 但沒有任何有效 Evidence 時降為 `NEEDS_REVIEW`。
- 因此整體判定可能比 LLM 自己回報的整體判定更嚴重。

## 撰寫原則

- **規則是純函式**：不碰 DB、不呼叫 LLM、無副作用。資料由 `AuditContext` 提供；寫入與 LLM 呼叫由 service 處理。
- **LLM 判定最高為 `WARNING`**：`ERROR` 這一版不由 LLM 產生。
- **`WARNING` 必須附至少一筆有效 Evidence**，否則降為 `NEEDS_REVIEW`。
- **資料不足就回 `NEEDS_REVIEW`**，不可猜測補完。
- **規則專屬驗證的訊息是模組常數**，不含病歷內容，可直接顯示給使用者。
- **單一規則的例外不影響其他規則**：service 把例外轉為 `FAILED`，只記錄例外類型，不記錄例外訊息（可能含病歷內容）。
- **院方沒有的資料不得推定**：沒有標記的檢驗、沒有選項清單的欄位，都不得判為正常或異常。

## 訊息用語

| ❌ 禁止 | ✅ 改用 |
|---|---|
| 護理師寫錯了 | 入院經過與身體評估內容不一致，請確認 |
| 沒有寫會診紀錄 | 2026-11-04 有胸腔內科會診，至期限 2026-11-05 的護理紀錄中未見相應紀錄，請確認（範例為虛構） |
| 抄襲昨天紀錄 | 今日紀錄與前日高度相似，但生命徵象已有變化，請確認是否需更新 |
| 違規 | 未見必要項目：○○、○○，請確認 |
| 漏寫、忘記、寫錯（R04、R06 的 `summary` 與 `message` 會被程式檢查） | 未見相應書寫，請確認 |

- 「不一致」「未見紀錄」「請確認」是系統的用語。不得指責護理師。
- 狀態文字（`status_label`）由後端回傳：`COMPLETED`→已完成、`NOT_APPLICABLE`→當日無此事件、`DATA_UNAVAILABLE`→院方尚未提供資料、`FAILED`→執行失敗（見 `services/audit/labels.py`）。
- 可稽核性文字（`AVAILABILITY_LABELS`）：`available`→可稽核、`not_applicable`→當日無此事件、`data_unavailable`→院方尚未提供資料、`day_not_ended`→當日尚未結束。
- 409 的固定訊息（不含病歷內容）：
  - 稽核日未結束：「當日尚未結束，隔日起才能稽核」（`DayNotEndedError`）。
  - 一次性規則已完成：「此項為每次入院一次的稽核，已完成，不可重複執行」（`RuleSettledError`）。

## 新增規則流程

1. 確認規則在清單內，且狀態允許實作（候選規則需先與護理長確認）。
2. 建立 `app/services/audit/rules/rNN_<name>.py`，實作 `AuditRule`。可參考 `r03_admission_completeness.py`（一次性）、`r04_assessment_followup.py`（每日）、`r06_consultation.py`（事件）。
3. 必要要素與門檻寫成模組常數；可調參數放 `core/config.py` 的 `Settings`，並同步 `.env.example`。
4. 建立 `app/prompts/rNN_<name>/v1.j2`，結構見 [llm.md](llm.md)。改版時新增 `v2.j2`，不修改已產出結果的版本。
5. 在 `services/audit/registry.py` 的 `RULE_REGISTRY` 加一行。
6. 補測試 `tests/services/audit/test_rNN_<name>.py`，LLM 一律以 mock 替代（可參考 `test_r03.py` 等）。
7. 更新本文件的規則清單與各規則的內容；若決策變更，更新 ADR 0011。

## 已知限制與資料來源

| 規則 | 資料來源（院方區塊） | 已知限制 |
|---|---|---|
| R01 | 入院經過、入院身體評估 | 沒有選項清單；身評未提到的項目不能判為不一致 |
| R02 | 護理記錄、生命徵象、檢驗（異常標記）、每日身評（管路） | 護理紀錄沒有時分；回溯資料只有 `data/` 內的天數；相似度只是參考值 |
| R03 | 工作清單（最新一天的檔案）、入院經過 | 沒有「不適用」狀態；「住院經過」以是否有入院經過紀錄判斷 |
| R04 | 每日身評、護理記錄、生命徵象、會診、用藥 | 院方未標示異常項目，由 LLM 依原文判斷；「防跌」「移動能力」是否納入待確認 |
| R05 | 轉床資料、護理記錄（轉出／轉入摘要類別）、身評（管路） | 院方沒有轉出／轉入摘要；轉床只有病房內換床（預留） |
| R06 | D−N 至 D 的會診及護理記錄（類別：會診、營養照會建議） | 沒有簽收與回覆時間；期限暫定；舊結果未依 `prompt_version` 過濾 |
| R07 | 用藥（PRN 藥囑）、護理記錄、生命徵象、檢驗 | 沒有給藥執行時間、執行者、高警訊標記（預留） |

- 資料歸日一律依紀錄本身的時間，不依資料夾日期（ADR 0011 決策 5）。
- 院方資料的 record_id 為內容雜湊（ADR 0011 決策 6）。

## 可調參數

| 設定（`core/config.py`） | 預設 | 用途 |
|---|---|---|
| `AUDIT_COPY_LOOKBACK_DAYS` | 5 | R02 回溯天數，含當日 |
| `AUDIT_CONSULT_FOLLOWUP_DAYS` | 1 | R06 每筆會診的追蹤期限日曆天數，暫定；院方待確認 |
| `LLM_MAX_RETRIES` | 2 | 格式不符時的重試次數（不含第一次呼叫） |
| `LLM_STRUCTURED_NUM_RETRIES` | 2 | 網路錯誤、429、逾時的重試次數（LiteLLM），與格式重試分開 |
| `LLM_MAX_CONCURRENCY` | 3 | 同時進行中的結構化 LLM 呼叫數 |

## 明確排除（不得實作）

錯別字、衛教後結果、出院準備、管路固定／引流系統、約束／防跌／翻身／身體護理、工作清單／醫藥囑簽收／簽章完成率。

- 注意：R04 的「防跌」排除項目與院方身評欄位（跌倒危險）之間的關係待護理長確認，見 ADR 0011 待確認事項。在確認前，程式不另外排除。

## 範圍外（屬臨床決策，不得實作）

藥物劑量正確性、藥物交互作用、診斷正確性、治療是否符合指引、病情惡化／敗血症／壓傷預測、自動產生護理計畫或治療建議。

## 候選規則（R08–R11）

| 代碼 | 必要要素 | 條件 |
|---|---|---|
| R08 | 是否說明、注意事項、可能併發症、追蹤病人理解情形 | 有侵入性檢查／治療 |
| R09 | 住院期間至少一次說明：作用／目的、副作用、注意事項 | 有藥囑執行 |
| R10 | 有自殺想法 → 通知主治醫師並紀錄；無 → 處置／轉介並紀錄 | 情緒困擾分數 ≥ 4 |
| R11 | `pending_consent_form == true` | 有待簽同意書 |

候選規則的條件與判定方式尚未與護理長確認，目前不實作。

## 待確認

| 項目 | 狀態 |
|---|---|
| R06 追蹤期限天數（`AUDIT_CONSULT_FOLLOWUP_DAYS` 暫定 1；ADR 0012 決策 2） | 待院方確認 |
| 一次性規則（R01、R03）完成後，入院評估被修改時的重跑入口（ADR 0012 待確認） | 待專案負責人決定 |
| 改版前 R06 舊結果的處理：清除、依 `prompt_version` 過濾，或維持現狀（ADR 0012 待確認） | 待決 |
| 未結束日期的病床總覽進度文字是否改為「當日尚未結束」（目前為「今日無可稽核項目」，ADR 0012 影響） | 待決 |
| R04 是否把「跌倒危險」「移動能力」視為需要追蹤的異常項目 | 待護理長確認 |
| R05、R07 所需的院方資料（轉出／轉入摘要、給藥執行紀錄） | 待院方確認 |
| R01、R03 的選項清單與「不適用」狀態 | 待院方確認 |
| 候選規則 R08–R11 是否納入第一版 | 待確認 |
