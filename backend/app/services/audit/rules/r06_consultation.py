"""R06 會診資訊↔護理紀錄（事件規則）。

當日有會診時，檢查每一筆會診在追蹤期限內，護理紀錄中是否有相應的書寫。第一版只看「有沒有對應紀錄」，
不比對建議內容；同一科多次會診靠內文的日期、時間、醫師分辨。

院方資料限制：會診只有時間與科別，沒有簽收時間、回覆時間與狀態，因此期限以會診時間起算，
期限為「當日＋`AUDIT_CONSULT_FOLLOWUP_DAYS`」（含當日）。若院方資料的最後一天早於期限最後一天，
期限內的後續資料尚未進來，找不到對應紀錄時只能回 NEEDS_REVIEW，不得判為 WARNING。
判定由 LLM 做，程式只整理事實並核對 Evidence。
"""

from datetime import timedelta
from typing import ClassVar, Final

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceRecord
from app.services.audit.rules.base import (
    AuditInput,
    Availability,
    available,
    not_applicable,
)

# 護理紀錄中，類別欄位為下列名稱者才視為會診後的對應書寫
FOLLOWUP_CATEGORIES: Final[tuple[str, ...]] = ("會診", "營養照會建議")
_CATEGORY_LABEL: Final = "類別"
_NO_DEPARTMENT: Final = "院方未提供科別"
_NO_CONSULT_REASON: Final = "當日沒有會診"
_DATA_COMPLETE: Final = "已到齊"
_DATA_INCOMPLETE: Final = "尚未到齊"
_INVALID_OUTPUT_MESSAGE: Final = "模型輸出的會診清單與紀錄不符，無法判定"
_UNMATCHED_VERDICT_MESSAGE: Final = "有會診未找到對應紀錄，整體判定不得為 PASS"
_INCOMPLETE_WARNING_MESSAGE: Final = "期限內資料尚未到齊時不得判為 WARNING"


class ConsultationMatch(BaseModel):
    """一筆會診在追蹤期限內是否找到對應的護理紀錄。"""

    record_id: str
    matched: bool


class R06Output(RuleOutput):
    """R06 的專屬欄位：每筆會診是否找到對應紀錄（存入結果的 details）。"""

    consultations: list[ConsultationMatch] = Field(default_factory=list)


class R06Consultation:
    """R06 規則。`followup_days` 未指定時讀取設定 `AUDIT_CONSULT_FOLLOWUP_DAYS`。"""

    code: ClassVar[str] = "R06"
    name: ClassVar[str] = "會診資訊↔護理紀錄"
    description: ClassVar[str] = (
        "當日會診之後，期限內是否有相應的護理紀錄（只看有無，不比對建議內容）。"
    )
    cycle: ClassVar[AuditCycle] = AuditCycle.EVENT
    prompt_name: ClassVar[str] = "r06_consultation"
    prompt_version: ClassVar[int] = 1
    output_schema: ClassVar[type[RuleOutput]] = R06Output

    def __init__(self, followup_days: int | None = None) -> None:
        self._followup_days = followup_days

    def check_availability(self, ctx: AuditContext) -> Availability:
        if not _consultations_on(ctx):
            return not_applicable(_NO_CONSULT_REASON)
        return available()

    def build_input(self, ctx: AuditContext) -> AuditInput:
        day = ctx.business_date
        end = day + timedelta(days=self._days())
        consultations = _consultations_on(ctx)
        notes = [
            record
            for record in ctx.records_between(day, end, RawRecordCategory.NURSING_PROGRESS_NOTE)
            if _is_followup_note(record)
        ]
        last_day = max(ctx.patient_dates)
        variables = {
            "window_start": day.isoformat(),
            "window_end": end.isoformat(),
            "last_data_date": last_day.isoformat(),
            "followup_data_status": _DATA_COMPLETE if last_day >= end else _DATA_INCOMPLETE,
            "consult_block": "\n".join(_consult_line(record) for record in consultations),
        }
        return AuditInput(variables=variables, records=(*consultations, *notes))

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        if not isinstance(output, R06Output):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        _check_coverage(output, audit_input)
        _check_verdict(output, audit_input)

    def _days(self) -> int:
        if self._followup_days is not None:
            return self._followup_days
        return get_settings().AUDIT_CONSULT_FOLLOWUP_DAYS


def _consultations_on(ctx: AuditContext) -> list[SourceRecord]:
    return ctx.records_on(ctx.business_date, RawRecordCategory.CONSULTATION)


def _is_followup_note(record: SourceRecord) -> bool:
    return any(
        field.label == _CATEGORY_LABEL and field.value in FOLLOWUP_CATEGORIES
        for field in record.fields
    )


def _consult_line(record: SourceRecord) -> str:
    return f"- record_id={record.record_id}｜時間：{record.time_text}｜科別：{_department(record)}"


def _department(record: SourceRecord) -> str:
    return next(
        (field.value for field in record.fields if field.label == _CATEGORY_LABEL),
        _NO_DEPARTMENT,
    )


def _check_coverage(output: R06Output, audit_input: AuditInput) -> None:
    """每筆會診都要有且只有一筆回覆，且 record_id 出自本次提供的會診紀錄。"""
    expected = {
        record.record_id
        for record in audit_input.records
        if record.source == RawRecordCategory.CONSULTATION
    }
    answered = [item.record_id for item in output.consultations]
    if len(answered) != len(set(answered)) or set(answered) != expected:
        raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)


def _check_verdict(output: R06Output, audit_input: AuditInput) -> None:
    """不得靜默判為 PASS；資料尚未到齊時不得以 WARNING 下結論。"""
    has_unmatched = any(not item.matched for item in output.consultations)
    if has_unmatched and output.verdict == "PASS":
        raise LLMOutputError(_UNMATCHED_VERDICT_MESSAGE)
    incomplete = audit_input.variables["followup_data_status"] == _DATA_INCOMPLETE
    if incomplete and any(finding.verdict == "WARNING" for finding in output.findings):
        raise LLMOutputError(_INCOMPLETE_WARNING_MESSAGE)
