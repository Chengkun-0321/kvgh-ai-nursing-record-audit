"""R03 入院護理評估完整性（一次性規則，範本）。

檢查工作清單各項與「住院經過」（入院經過）是否有填寫。院方名稱與 PDF 名稱略異，
對照表寫在本模組的常數，由程式注入 prompt，不在模板內重複寫死。
判定由 LLM 做，程式只整理事實並核對 Evidence。
"""

from typing import ClassVar, Final

from pydantic import Field

from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceRecord, from_checklist
from app.services.audit.rules.base import AuditInput, Availability, available, data_unavailable

# (PDF 項目名稱, 院方工作清單欄位名稱)；「住院經過」不在工作清單內，改看入院經過紀錄
REQUIRED_ITEMS: Final[tuple[tuple[str, str | None], ...]] = (
    ("基本資料", "基本資料"),
    ("個人病史", "個人病史"),
    ("營養評估", "營養評估"),
    ("日常生活型態", "日常生活"),
    ("身體評估", "身體評估"),
    ("心靈社會", "心理評估"),
    ("住院經過", None),
    ("環境", "環境"),
)
_ITEM_NAMES: Final = frozenset(name for name, _ in REQUIRED_ITEMS)
_NO_CHECKLIST_REASON: Final = "院方未提供工作清單，本項目目前無法判斷。"
_COURSE_PRESENT: Final = "有內容"
_COURSE_ABSENT: Final = "無內容或院方未提供"
_INVALID_ITEM_MESSAGE: Final = "模型輸出的項目不在必要項目清單內，無法判定"


class R03Output(RuleOutput):
    """R03 的專屬欄位：未完成的必要項目（存入結果的 details）。"""

    incomplete_items: list[str] = Field(default_factory=list)


class R03AdmissionCompleteness:
    """R03 規則。"""

    code: ClassVar[str] = "R03"
    name: ClassVar[str] = "入院護理評估完整性"
    description: ClassVar[str] = (
        "入院護理評估的工作清單各項與住院經過是否都已填寫，列出未完成的項目。"
    )
    cycle: ClassVar[AuditCycle] = AuditCycle.ONCE_PER_ADMISSION
    prompt_name: ClassVar[str] = "r03_admission_completeness"
    prompt_version: ClassVar[int] = 1
    output_schema: ClassVar[type[RuleOutput]] = R03Output

    def check_availability(self, ctx: AuditContext) -> Availability:
        if ctx.work_checklist.total_count == 0:
            return data_unavailable(_NO_CHECKLIST_REASON)
        return available()

    def build_input(self, ctx: AuditContext) -> AuditInput:
        checklist_record = from_checklist(ctx.work_checklist, ctx.business_date)
        course_records: list[SourceRecord] = ctx.records_of(RawRecordCategory.ADMISSION_COURSE)
        variables = {
            "checklist_block": _checklist_lines(checklist_record),
            "required_items_block": _required_items_lines(),
            "admission_course_status": _COURSE_PRESENT if course_records else _COURSE_ABSENT,
        }
        return AuditInput(variables=variables, records=(checklist_record, *course_records))

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        if not isinstance(output, R03Output):
            raise LLMOutputError(_INVALID_ITEM_MESSAGE)
        named = [finding.item for finding in output.findings] + output.incomplete_items
        if any(item not in _ITEM_NAMES for item in named):
            raise LLMOutputError(_INVALID_ITEM_MESSAGE)


def _checklist_lines(checklist_record: SourceRecord) -> str:
    return "\n".join(f"{field.label}：{field.value}" for field in checklist_record.fields)


def _required_items_lines() -> str:
    lines = []
    for pdf_name, hospital_name in REQUIRED_ITEMS:
        if hospital_name is None:
            lines.append(f"- {pdf_name}（對應院方的入院經過紀錄）")
        else:
            lines.append(f"- {pdf_name}（對應工作清單欄位：{hospital_name}）")
    return "\n".join(lines)
