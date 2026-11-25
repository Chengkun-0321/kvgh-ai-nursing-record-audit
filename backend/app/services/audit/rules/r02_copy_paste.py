"""R02 紀錄複製／一成不變／時效性（每日規則）。

程式只整理回溯期間內的事實與相似度參考值，判定全部交給 LLM（見 prompt r02_copy_paste/v1.j2）。
回溯天數取自 Settings 的 AUDIT_COPY_LOOKBACK_DAYS（含當日）；資料不足時有幾天用幾天。
"""

from datetime import date
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceRecord, abnormal_only
from app.services.audit.rules.base import AuditInput, Availability, available, not_applicable
from app.services.audit.rules.r02_comparison import (
    compare_notes,
    note_category,
    render_alignment_block,
    similarity_fact,
    tube_only,
    window_start,
)

NOTE_SOURCE: Final = RawRecordCategory.NURSING_PROGRESS_NOTE.value
VITAL_SOURCE: Final = RawRecordCategory.VITAL_SIGN.value
LAB_SOURCE: Final = RawRecordCategory.LAB_RESULT.value
ASSESSMENT_SOURCE: Final = RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT.value
# 不屬於護理類別的固定項目名稱：生命徵象、檢驗、身評管路
FIXED_ITEMS: Final = frozenset({"生命徵象", "檢驗", "管路"})
_NOT_APPLICABLE_REASON: Final = "當日沒有護理紀錄，本項不適用。"
_NO_PRIOR_STATUS: Final = "沒有前幾日紀錄可比對，只能檢查時效性（生命徵象引用是否為當日值）"
_HAS_PRIOR_STATUS: Final = "有前幾日紀錄可比對"
_INVALID_OUTPUT_MESSAGE: Final = "模型輸出的類別或項目不在輸入資料內，無法判定"
_UNCOMPARABLE_JUDGEMENT_MESSAGE: Final = "模型對沒有前幾日紀錄的類別給出比對結論，無法判定"


class CategoryJudgement(BaseModel):
    """LLM 對一個當日護理類別的比對結論（程式的相似度僅為參考）。"""

    category: str
    judgement: Literal["幾乎相同", "有實質差異", "無法判斷"]


class R02Output(RuleOutput):
    """R02 的專屬欄位：各當日類別的比對結論（存入結果的 details）。"""

    category_judgements: list[CategoryJudgement] = Field(default_factory=list)


class R02CopyPaste:
    """R02 規則。"""

    code: ClassVar[str] = "R02"
    name: ClassVar[str] = "紀錄複製／一成不變／時效性"
    short_name: ClassVar[str] = "複製／時效"
    description: ClassVar[str] = (
        "近幾日護理紀錄是否與前日幾乎相同，且生命徵象等臨床資料已變化卻未反映。"
    )
    cycle: ClassVar[AuditCycle] = AuditCycle.DAILY
    prompt_name: ClassVar[str] = "r02_copy_paste"
    prompt_version: ClassVar[int] = 1
    output_schema: ClassVar[type[RuleOutput]] = R02Output

    def check_availability(self, ctx: AuditContext) -> Availability:
        if not ctx.records_on(ctx.business_date, NOTE_SOURCE):
            return not_applicable(_NOT_APPLICABLE_REASON)
        return available()

    def build_input(self, ctx: AuditContext) -> AuditInput:
        today = ctx.business_date
        start = window_start(today, get_settings().AUDIT_COPY_LOOKBACK_DAYS)
        notes = sorted(
            ctx.records_between(start, today, NOTE_SOURCE),
            key=lambda record: (note_category(record), record.business_date),
        )
        records = (
            *notes,
            *ctx.records_between(start, today, VITAL_SOURCE),
            *_abnormal_labs(ctx.records_between(start, today, LAB_SOURCE)),
            *_tube_records(ctx.records_between(start, today, ASSESSMENT_SOURCE)),
        )
        comparisons = compare_notes(notes, today)
        has_prior = any(item.prior is not None for item in comparisons)
        variables = {
            "copy_window_block": _window_text(start, today, records),
            "comparison_status": _HAS_PRIOR_STATUS if has_prior else _NO_PRIOR_STATUS,
            "category_alignment_block": render_alignment_block(comparisons),
        }
        facts = {"similarities": [similarity_fact(item) for item in comparisons]}
        return AuditInput(variables=variables, records=records, facts=facts)

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        if not isinstance(output, R02Output):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        categories = _note_categories(audit_input.records)
        if any(item not in categories | FIXED_ITEMS for item in _finding_items(output)):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        today_categories, comparable = _today_and_comparable(audit_input.records)
        for judgement in output.category_judgements:
            if judgement.category not in today_categories:
                raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
            if judgement.category not in comparable and judgement.judgement != "無法判斷":
                raise LLMOutputError(_UNCOMPARABLE_JUDGEMENT_MESSAGE)


def _abnormal_labs(labs: list[SourceRecord]) -> list[SourceRecord]:
    return [lab for lab in (abnormal_only(record) for record in labs) if lab is not None]


def _tube_records(assessments: list[SourceRecord]) -> list[SourceRecord]:
    return [tube for tube in (tube_only(record) for record in assessments) if tube is not None]


def _window_text(start: date, today: date, records: tuple[SourceRecord, ...]) -> str:
    days = sorted({record.business_date.isoformat() for record in records})
    day_text = "、".join(days) if days else "無"
    return (
        f"回溯期間：{start.isoformat()} 至 {today.isoformat()}（含當日）。"
        f"院方實際有資料的日期：{day_text}。"
    )


def _finding_items(output: R02Output) -> list[str]:
    return [finding.item for finding in output.findings]


def _note_categories(records: tuple[SourceRecord, ...]) -> set[str]:
    return {note_category(record) for record in records if record.source == NOTE_SOURCE}


def _today_and_comparable(records: tuple[SourceRecord, ...]) -> tuple[set[str], set[str]]:
    """當日有紀錄的類別，以及其中在前幾日也有同類別紀錄（可比對）的類別。"""
    notes = [record for record in records if record.source == NOTE_SOURCE]
    if not notes:
        return set(), set()
    today = max(record.business_date for record in notes)
    today_categories = {note_category(r) for r in notes if r.business_date == today}
    prior_categories = {note_category(r) for r in notes if r.business_date < today}
    return today_categories, today_categories & prior_categories
