"""R04 每日身體評估異常追蹤（每日規則）。

系統把當日身評的全部欄位原文、當日全部護理紀錄，以及輔助資料（生命徵象、會診、用藥）交給 LLM。
LLM 依欄位原文判斷哪些項目異常，再判斷當日護理紀錄是否有相應的描述、處置或追蹤。
院方沒有標示異常項目，判斷準則寫在 prompt；程式只核對項目名稱、判定對應與依據來源。
"""

from typing import ClassVar, Final

from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.rules.base import AuditInput, Availability, available, not_applicable
from app.services.audit.rules.r04_checks import assessment_item_names, validate_r04_output
from app.services.audit.rules.r04_output import R04Output

_ASSESSMENT: Final = RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT
_NURSING: Final = RawRecordCategory.NURSING_PROGRESS_NOTE
# 輔助資料只當背景，不能取代護理紀錄的書寫
_AUXILIARY: Final = (
    RawRecordCategory.VITAL_SIGN,
    RawRecordCategory.CONSULTATION,
    RawRecordCategory.MEDICATION_ORDER,
)
_NO_ASSESSMENT_REASON: Final = "當日沒有每日身體評估"
_INVALID_OUTPUT_MESSAGE: Final = "模型輸出不是 R04 的結構，無法判定"
_NO_ITEMS_TEXT: Final = "（當日身評沒有欄位）"
_NURSING_PRESENT: Final = (
    '當日有 {count} 筆護理紀錄，見下方 source="nursing_progress_note" 的紀錄。'
)
# 資料中未見護理紀錄，不能推定為未書寫，因此全部改判為 UNCERTAIN
_NURSING_ABSENT: Final = (
    "當日沒有護理紀錄。資料中未見紀錄不代表未書寫，所有可能的異常項目請判為 UNCERTAIN。"
)


class R04AssessmentFollowup:
    """R04 規則：每日身評異常項目，在當日護理紀錄中是否有相應書寫。"""

    code: ClassVar[str] = "R04"
    name: ClassVar[str] = "身評異常追蹤"
    short_name: ClassVar[str] = "異常追蹤"
    description: ClassVar[str] = "當日每日身體評估的異常項目，在護理紀錄中是否有描述、處置或追蹤。"
    cycle: ClassVar[AuditCycle] = AuditCycle.DAILY
    prompt_name: ClassVar[str] = "r04_assessment_followup"
    prompt_version: ClassVar[int] = 1
    output_schema: ClassVar[type[RuleOutput]] = R04Output

    def check_availability(self, ctx: AuditContext) -> Availability:
        if ctx.records_on(ctx.business_date, _ASSESSMENT):
            return available()
        return not_applicable(_NO_ASSESSMENT_REASON)

    def build_input(self, ctx: AuditContext) -> AuditInput:
        day = ctx.business_date
        assessments = ctx.records_on(day, _ASSESSMENT)
        nursing = ctx.records_on(day, _NURSING)
        auxiliary = [record for source in _AUXILIARY for record in ctx.records_on(day, source)]
        variables = {
            "assessment_items_block": _items_block(assessment_item_names(assessments)),
            "nursing_note_status": _nursing_status(len(nursing)),
        }
        return AuditInput(
            variables=variables,
            records=(*assessments, *nursing, *auxiliary),
        )

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        if not isinstance(output, R04Output):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        assessments = [record for record in audit_input.records if record.source == _ASSESSMENT]
        validate_r04_output(output, assessments)


def _items_block(names: list[str]) -> str:
    if not names:
        return _NO_ITEMS_TEXT
    return "\n".join(f"- {name}" for name in names)


def _nursing_status(count: int) -> str:
    if count == 0:
        return _NURSING_ABSENT
    return _NURSING_PRESENT.format(count=count)
