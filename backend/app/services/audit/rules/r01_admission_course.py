"""R01 入院經過↔入院身體評估一致性（入院規則）。

檢查兩件事：入院經過是否提到五項必要要素（發生時間、不適症狀、就醫經過、處理、住院原因），
以及入院經過與入院身體評估是否相符。院方只提供有勾選或有填寫的內容，身評「沒有提到」某項
不代表正常或異常，因此不據此判為不一致（限制寫在 prompt）。
判定由 LLM 做，程式只整理事實並核對 Evidence。
"""

from collections.abc import Mapping
from typing import ClassVar, Final

from pydantic import BaseModel, Field

from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.rules.base import AuditInput, Availability, available, data_unavailable

REQUIRED_ELEMENTS: Final[tuple[str, ...]] = (
    "發生時間",
    "不適症狀",
    "就醫經過",
    "處理",
    "住院原因",
)
_NO_COURSE_REASON: Final = "院方未提供入院經過，本項目目前無法判斷。"
_NO_ASSESSMENT_REASON: Final = "院方未提供入院身體評估，本項目目前無法判斷。"
_NOT_PROVIDED: Final = "院方未提供"
_INVALID_OUTPUT_MESSAGE: Final = "模型輸出的必要要素不完整或名稱不符，無法判定"
# 模型判定「未提及」的要素：不是判斷不了，所以不沿用「無法判定」
_UNMENTIONED_LABEL: Final = "未見紀錄"
_UNMENTIONED_VERDICT_MESSAGE: Final = "入院經過有必要要素未提及，整體判定不得為 PASS"


class ElementMention(BaseModel):
    """一項必要要素是否在入院經過中提及。"""

    element: str
    mentioned: bool


class R01Output(RuleOutput):
    """R01 的專屬欄位：五項要素各自是否提及（存入結果的 details）。"""

    elements: list[ElementMention] = Field(default_factory=list)


class R01AdmissionCourse:
    """R01 規則：入院經過與入院身體評估的一致性，以及五項必要要素。"""

    code: ClassVar[str] = "R01"
    name: ClassVar[str] = "入院經過↔身體評估一致性"
    short_name: ClassVar[str] = "經過↔身評"
    description: ClassVar[str] = "入院經過與入院身體評估是否相符，並檢查五項必要要素是否提及。"
    cycle: ClassVar[AuditCycle] = AuditCycle.ONCE_PER_ADMISSION
    prompt_name: ClassVar[str] = "r01_admission_course"
    prompt_version: ClassVar[int] = 1
    output_schema: ClassVar[type[RuleOutput]] = R01Output

    def check_availability(self, ctx: AuditContext) -> Availability:
        if not ctx.records_of(RawRecordCategory.ADMISSION_COURSE):
            return data_unavailable(_NO_COURSE_REASON)
        if not ctx.records_of(RawRecordCategory.ADMISSION_ASSESSMENT):
            return data_unavailable(_NO_ASSESSMENT_REASON)
        return available()

    def build_input(self, ctx: AuditContext) -> AuditInput:
        course = ctx.records_of(RawRecordCategory.ADMISSION_COURSE)
        assessment = ctx.records_of(RawRecordCategory.ADMISSION_ASSESSMENT)
        variables = {
            "admitted_at_text": ctx.admitted_at_text or _NOT_PROVIDED,
            "required_elements_block": _elements_lines(),
        }
        return AuditInput(variables=variables, records=(*course, *assessment))

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        if not isinstance(output, R01Output):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        names = [item.element for item in output.elements]
        if sorted(names) != sorted(REQUIRED_ELEMENTS):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        if output.verdict == "PASS" and not all(item.mentioned for item in output.elements):
            raise LLMOutputError(_UNMENTIONED_VERDICT_MESSAGE)

    def finding_labels(self, details: Mapping[str, object] | None) -> Mapping[str, str]:
        """未提及的必要要素顯示「未見紀錄」。"""
        return dict.fromkeys(_unmentioned_elements(details), _UNMENTIONED_LABEL)


def _unmentioned_elements(details: Mapping[str, object] | None) -> list[str]:
    elements = (details or {}).get("elements")
    if not isinstance(elements, list):
        return []
    mentions = [ElementMention.model_validate(item) for item in elements]
    return [item.element for item in mentions if not item.mentioned]


def _elements_lines() -> str:
    return "\n".join(f"- {name}" for name in REQUIRED_ELEMENTS)
