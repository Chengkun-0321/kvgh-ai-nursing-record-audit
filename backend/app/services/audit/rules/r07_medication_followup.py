"""R07 給藥後療效與不良反應追蹤（事件規則，預留模組：目前不判斷）。

院方資料目前只有需要時給藥（PRN）的藥囑，沒有給藥執行時間、執行者、高警訊用藥標記與追蹤紀錄。
因此 `check_availability` 一律回傳 DATA_UNAVAILABLE，流程不呼叫 LLM，只寫入一筆紀錄。

`build_input` 已依預期的資料形狀實作（當日用藥、當日全部護理紀錄；輔助：當日生命徵象、當日檢驗），
目前不會被呼叫到，以虛構資料測試通過。

資料到位後要改的地方：
1. `check_availability`：改為依院方資料判斷。有需追蹤的給藥 → AVAILABLE；
   當日無此類給藥 → NOT_APPLICABLE。
2. `_followup_candidates`：目前以當日全部用藥紀錄為候選；院方提供「需追蹤」標記後改為依標記篩選。
3. 檢驗：目前整批送入（見下方說明）；共用介面補上異常旗標後，改為只送異常項目。
4. 給藥後追蹤時限：尚待院方確認，prompt 不寫死時限；確認後由 prompt 變數注入。

待院方確認：需追蹤藥品的判定標準、追蹤時限、執行紀錄的欄位。
目前限制：`SourceRecord` 未保留檢驗的異常旗標，「當日異常檢驗」暫時送入當日全部檢驗紀錄，
若要只送異常項目，需於共用的 records.py 補上旗標（共用介面，本模組未改）。
"""

from datetime import date
from typing import ClassVar, Final

from pydantic import BaseModel, Field

from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceRecord
from app.services.audit.rules.base import AuditInput, Availability, data_unavailable

# 護理紀錄與用藥紀錄的欄位標籤（與 services/audit/records.py 的合成欄位名稱一致）
TITLE_LABEL: Final = "標題"
# 療效、副作用與不良反應發生時，院方要求的處置（由程式注入 prompt）
RESPONSE_ELEMENTS: Final = ("通知醫師", "處理", "通報", "紀錄")
RESPONSE_ITEM: Final = "異常或不良反應處置"
_REASON: Final = (
    "院方尚未提供所需資料：院方資料只有需要時給藥（PRN）的藥囑，"
    "沒有給藥執行時間、執行者、高警訊用藥標記與追蹤紀錄，本項目目前無法判斷。"
)
_INVALID_OUTPUT_MESSAGE: Final = "模型輸出的藥品或項目不在當日用藥清單內，無法判定"


class MedicationFollowupMention(BaseModel):
    """一個藥品的療效與副作用追蹤是否有書寫。"""

    drug: str
    effect_described: bool
    side_effect_described: bool


class R07Output(RuleOutput):
    """R07 的專屬欄位：每個藥品的療效與副作用追蹤是否有書寫（存入結果的 details）。"""

    medications: list[MedicationFollowupMention] = Field(default_factory=list)


class R07MedicationFollowup:
    """R07 規則；目前預留，`check_availability` 一律回傳 DATA_UNAVAILABLE。"""

    code: ClassVar[str] = "R07"
    name: ClassVar[str] = "給藥後療效與不良反應追蹤"
    description: ClassVar[str] = (
        "需追蹤之給藥後，療效、副作用與不良反應是否有通知、處理與紀錄。"
        "院方目前只有 PRN 藥囑，本項不判斷。"
    )
    cycle: ClassVar[AuditCycle] = AuditCycle.EVENT
    prompt_name: ClassVar[str] = "r07_medication_followup"
    prompt_version: ClassVar[int] = 1
    output_schema: ClassVar[type[RuleOutput]] = R07Output

    def check_availability(self, ctx: AuditContext) -> Availability:
        return data_unavailable(_REASON)

    def build_input(self, ctx: AuditContext) -> AuditInput:
        day = ctx.business_date
        medications = _followup_candidates(ctx, day)
        nursing = ctx.records_on(day, RawRecordCategory.NURSING_PROGRESS_NOTE.value)
        vitals = ctx.records_on(day, RawRecordCategory.VITAL_SIGN.value)
        labs = ctx.records_on(day, RawRecordCategory.LAB_RESULT.value)
        drug_names = _drug_names(medications)
        variables = {
            "drug_names_block": "\n".join(f"- {name}" for name in drug_names) or "本日沒有用藥紀錄",
            "response_elements_block": "、".join(RESPONSE_ELEMENTS),
            "medication_status": _count_status(medications, "本日有用藥紀錄", "本日沒有用藥紀錄"),
            "nursing_status": _count_status(nursing, "本日有護理紀錄", "本日沒有護理紀錄"),
            "vital_status": _count_status(vitals, "本日有生命徵象", "本日未見生命徵象"),
            "lab_status": _count_status(labs, "本日有檢驗結果", "本日未見檢驗結果"),
        }
        records = (*medications, *nursing, *vitals, *labs)
        return AuditInput(variables=variables, records=records)

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        if not isinstance(output, R07Output):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        allowed = _allowed_items(audit_input)
        if any(mention.drug not in allowed for mention in output.medications):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        if any(finding.item not in allowed for finding in output.findings):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)


def _followup_candidates(ctx: AuditContext, day: date) -> list[SourceRecord]:
    """需評估追蹤的給藥紀錄；目前為當日全部用藥紀錄（見模組說明）。"""
    return ctx.records_on(day, RawRecordCategory.MEDICATION_ORDER.value)


def _drug_names(medications: list[SourceRecord]) -> list[str]:
    names = (_title(record) for record in medications)
    return [name for name in names if name]


def _title(record: SourceRecord) -> str | None:
    return next((field.value for field in record.fields if field.label == TITLE_LABEL), None)


def _allowed_items(audit_input: AuditInput) -> frozenset[str]:
    """藥品名稱（來自本次輸入的用藥紀錄）與處置項目；LLM 只能引用這些名稱。"""
    medications = [
        record
        for record in audit_input.records
        if record.source == RawRecordCategory.MEDICATION_ORDER.value
    ]
    return frozenset({*_drug_names(medications), RESPONSE_ITEM})


def _count_status(records: list[SourceRecord], found: str, none: str) -> str:
    return f"{found}（{len(records)} 筆）" if records else none
