# 稽核規則規範

來源：專案外部文件 `高榮護理師workflow/20260916高榮護理師需求確認/依據9:11稽核項目需求確認.md`（護理長 9/11 稽核討論 PDF 整理）。
**只實作本清單內的規則；清單變更需先與護理長確認，再更新本文件。**

## 規則清單

| 代碼 | 稽核項目 | 觸發條件 | 建議 engine | 狀態 |
|---|---|---|---|---|
| R01 | 入院經過 ↔ 身體評估一致性 | 新入院 | llm | ✅ 確定 |
| R02 | 近 3 日紀錄複製／一成不變／時效性 | 每日 | hybrid | ✅ 確定 |
| R03 | 入院護理評估指定項目完整性 | 新入院 | rule | ✅ 確定 |
| R04 | 每日身體評估異常 ↔ 後續追蹤紀錄 | 當日身評有異常項目 | hybrid | ✅ 確定 |
| R05 | 轉入／轉出摘要完整性 | 轉入／轉出事件 | llm | ✅ 確定 |
| R06 | 會診資訊 ↔ 護理紀錄 | 當日有會診 | hybrid | ✅ 確定 |
| R07 | 給藥後療效／副作用／不良反應追蹤 | 當日有需追蹤之給藥 | hybrid | ✅ 確定 |
| R08 | 侵入性檢查／治療前說明 | 有侵入性檢查／治療 | hybrid | 🟡 候選（高度可行） |
| R09 | 藥物執行前衛教 | 有藥囑執行 | hybrid | 🟡 候選（高度可行） |
| R10 | 情緒困擾 ≥ 4 後續處置紀錄 | 情緒困擾分數 ≥ 4 | hybrid | 🟡 候選（待確認） |
| R11 | 待簽同意書提醒 | 有待簽同意書 | rule | 🟡 候選（報表附加項） |

- 候選規則（R08–R11）實作後預設關閉，由設定 `ENABLED_AUDIT_RULES` 開啟
- engine：`rule` = 純程式判斷；`llm` = 需語意理解；`hybrid` = 程式先篩選／比對，LLM 只處理語意部分

### 各規則必要要素

| 代碼 | 必要要素（寫成規則模組常數，prompt 由程式注入） |
|---|---|
| R01 | 發生時間、不適症狀、就醫經過、處理、住院原因；並與身體評估交叉比對 |
| R02 | 與前 1–2 日紀錄相似度（門檻待決）；相似但生命徵象／檢驗／管路等臨床資料已變化 → 提醒；引用資料日期是否為當日 |
| R03 | 基本資料、個人病史、營養評估、日常生活型態、身體評估、心靈社會、住院經過、環境 |
| R04 | 異常項目是否在過程紀錄中被描述、處置、追蹤 |
| R05 | 轉出：住院期間重要檢查、治療結果、目前病況、管路、傷口、健康問題、轉出原因；轉入：意識、呼吸、身體活動、管路、皮膚狀況 |
| R06 | 會診後過程紀錄是否有相應書寫 |
| R07 | 療效、副作用、不良反應時是否通知醫師、處理、通報、紀錄 |
| R08 | 是否說明、注意事項、可能併發症、追蹤病人理解情形 |
| R09 | 住院期間至少一次說明：作用／目的、副作用、注意事項 |
| R10 | 有自殺想法 → 通知主治醫師並紀錄；無 → 處置／轉介並紀錄 |
| R11 | `pending_consent_form == true` |

### 明確排除（不得實作）

錯別字、衛教後結果、出院準備、管路固定／引流系統、約束／防跌／翻身／身體護理、工作清單／醫藥囑簽收／簽章完成率。

### 範圍外（屬臨床決策，不得實作）

藥物劑量正確性、藥物交互作用、診斷正確性、治療是否符合指引、病情惡化／敗血症／壓傷預測、自動產生護理計畫或治療建議。

## 介面

```python
# app/core/enums.py
class Verdict(StrEnum):
    PASS = "PASS"                  # 未發現問題
    WARNING = "WARNING"            # 疑似缺漏／不一致，需人工確認
    ERROR = "ERROR"                # 依明確規則可確認缺漏
    NEEDS_REVIEW = "NEEDS_REVIEW"  # 系統無法判定（資料不足、LLM 失敗）

class Engine(StrEnum):
    RULE = "rule"
    LLM = "llm"
    HYBRID = "hybrid"

# app/schemas/audit.py
class Evidence(BaseModel):
    source: str               # glossary 中的資料來源名稱，如 "nursing_progress_note"
    record_id: str
    field: str | None
    recorded_at: datetime | None
    excerpt: str | None       # 原文片段，必須能在來源資料中找到

class AuditFinding(BaseModel):
    rule_code: str
    patient_key: str
    business_date: date
    verdict: Verdict
    message: str              # 繁中、提醒語氣
    evidence: list[Evidence]
    engine: Engine
    model: str | None         # LLM 規則才有
    prompt_version: str | None

# app/services/audit/base.py
class AuditRule(Protocol):
    code: ClassVar[str]
    name: ClassVar[str]
    engine: ClassVar[Engine]

    def applies_to(self, ctx: AuditContext) -> bool: ...
    async def evaluate(self, ctx: AuditContext) -> AuditFinding: ...
```

## 規則撰寫原則

- **規則不得存取 DB 或外部服務**：所需資料由 `AuditContext` 提供；LLM 只能透過注入的 gateway 呼叫
- 規則無副作用：只回傳 `AuditFinding`，由 runner 統一寫入
- `WARNING` 以上必須附至少一筆 Evidence
- **暫定**：`ERROR` 只用於 `rule` engine 且證據客觀可驗證；LLM 判斷最高只到 `WARNING`
- 單一規則失敗不影響其他規則：runner 捕捉例外並記為 `NEEDS_REVIEW`
- LLM 併發數由設定 `LLM_MAX_CONCURRENCY` 控制（`asyncio.Semaphore`）

## 訊息用語

| ❌ 禁止 | ✅ 改用 |
|---|---|
| 護理師寫錯了 | 入院經過與身體評估內容不一致，請確認 |
| 沒有寫會診紀錄 | 今日有會診，過程紀錄中未見相應紀錄，請確認 |
| 抄襲昨天紀錄 | 今日紀錄與前日高度相似，但生命徵象已有變化，請確認是否需更新 |
| 違規 | 未見必要項目：○○、○○，請確認 |

## 新增規則流程

1. 確認規則在清單內，且狀態允許實作
2. 建立 `app/services/audit/rules/rNN_<name>.py`，實作 `AuditRule`
3. 必要要素、門檻放模組常數或 `Settings`
4. 需要 LLM → 建立 `app/prompts/rNN_<name>/v1.j2`（見 [llm.md](llm.md)）
5. 註冊到 `RULE_REGISTRY`；候選規則受 `ENABLED_AUDIT_RULES` 控制
6. 建議（非強制）準備正例＋反例 fixture，方便與護理長對照
7. 更新本文件規則清單
