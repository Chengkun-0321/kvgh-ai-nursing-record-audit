"""R06 會診資訊↔護理紀錄：截至稽核日的逐筆期限追蹤。

納入 D−N 至 D（含）的會診與指定類別護理紀錄，逐筆提供到期日、是否已到期及資料狀態。
LLM 判斷期限內是否已有對應書寫；寬限期中不是缺漏。會診日早於最早資料日時，
已到期但未見對應紀錄只能 NEEDS_REVIEW。程式只整理事實並驗證輸出，不碰 DB 或呼叫 LLM。
"""

import re
from collections.abc import Mapping
from datetime import date, timedelta
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import LlmFinding, RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceRecord
from app.services.audit.rules.base import AuditInput, Availability, available, not_applicable

FOLLOWUP_CATEGORIES: Final[tuple[str, ...]] = ("會診", "營養照會建議")
_CATEGORY_LABEL: Final = "類別"
_NO_DEPARTMENT: Final = "院方未提供科別"
_NO_CONSULT_REASON: Final = "追蹤範圍內沒有會診"
_PHYSICIAN_NOTE_PATTERN: Final = re.compile(r"[(（].*$")
_DATA_COMPLETE: Final = "已到齊"
_DATA_INCOMPLETE: Final = "尚未到齊"
_GRACE_LABEL: Final = "寬限期中"
_INVALID_OUTPUT_MESSAGE: Final = "模型輸出的會診清單與紀錄不符，無法判定"
_DEADLINE_MESSAGE: Final = "模型輸出的會診狀態與追蹤期限不一致，無法判定"
_VERDICT_MESSAGE: Final = "模型輸出的整體判定與會診狀態不一致，無法判定"
_INCOMPLETE_WARNING_MESSAGE: Final = "期限內資料尚未到齊的會診不得判為 WARNING"
_FINDING_MESSAGE: Final = "模型輸出的發現與會診項目或狀態不一致，無法判定"
_SOURCE_MESSAGE: Final = "模型輸出的依據與會診或追蹤期限不符，無法判定"
_WORDING_MESSAGE: Final = "模型輸出用語不符合提醒原則，無法判定"
_FORBIDDEN_WORDS: Final = ("寫錯", "漏寫", "違規", "忘記")

ConsultationStatus = Literal["MATCHED", "IN_GRACE", "NOT_FOUND"]


class ConsultationMatch(BaseModel):
    """一筆會診的追蹤狀態；item 與同位置的 finding 對應。"""

    record_id: str
    item: str
    status: ConsultationStatus


class R06Output(RuleOutput):
    """逐筆會診狀態存入 details；findings 與 consultations 依相同順序排列。"""

    consultations: list[ConsultationMatch] = Field(default_factory=list)


class _ConsultationFacts(BaseModel):
    """程式計算的逐筆事實；供 prompt、輸出核對與結果保存共用。"""

    record_id: str
    item: str
    deadline: date
    is_due: bool
    data_complete: bool


class R06Consultation:
    """截至稽核日追蹤會診；未指定 followup_days 時讀取設定的日曆天數。"""

    code: ClassVar[str] = "R06"
    name: ClassVar[str] = "會診資訊↔護理紀錄"
    short_name: ClassVar[str] = "會診"
    description: ClassVar[str] = (
        "截至稽核日，追蹤範圍內的會診是否已見期限內對應護理紀錄；"
        "寬限期中不是缺漏，已到期而未見紀錄時提醒確認（只看有無，不比對建議內容）。"
    )
    cycle: ClassVar[AuditCycle] = AuditCycle.EVENT
    prompt_name: ClassVar[str] = "r06_consultation"
    prompt_version: ClassVar[int] = 3
    output_schema: ClassVar[type[RuleOutput]] = R06Output

    def __init__(self, followup_days: int | None = None) -> None:
        self._followup_days = followup_days

    def check_availability(self, ctx: AuditContext) -> Availability:
        """追蹤範圍內有任何會診即可稽核，包含寬限期中的會診。"""
        return available() if self._consultations(ctx) else not_applicable(_NO_CONSULT_REASON)

    def build_input(self, ctx: AuditContext) -> AuditInput:
        """整理截至稽核日的會診、護理紀錄及逐筆期限事實。"""
        start = ctx.business_date - timedelta(days=self._days())
        consultations = self._consultations(ctx)
        notes = [
            record
            for record in ctx.records_between(
                start, ctx.business_date, RawRecordCategory.NURSING_PROGRESS_NOTE
            )
            if _is_followup_note(record)
        ]
        facts = [_consult_facts(record, ctx, self._days()) for record in consultations]
        variables = {
            "window_start": start.isoformat(),
            "window_end": ctx.business_date.isoformat(),
            "followup_days": str(self._days()),
            "earliest_data_date": min(ctx.patient_dates).isoformat(),
            "followup_categories": "、".join(FOLLOWUP_CATEGORIES),
            "consult_block": "\n".join(
                _consult_line(record, fact)
                for record, fact in zip(consultations, facts, strict=True)
            ),
        }
        return AuditInput(
            variables=variables,
            records=(*consultations, *notes),
            facts={"consultation_facts": [fact.model_dump(mode="json") for fact in facts]},
        )

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        """核對覆蓋、期限、判定、逐筆 finding、依據來源與提醒用語。"""
        if not isinstance(output, R06Output):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        _check_coverage(output, audit_input)
        entries = audit_input.facts.get("consultation_facts")
        if not isinstance(entries, list):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        facts = {
            fact.record_id: fact
            for fact in (_ConsultationFacts.model_validate(item) for item in entries)
        }
        _check_findings(output, facts, audit_input)
        _check_verdict(output)
        texts = [output.summary, *(finding.message for finding in output.findings)]
        if any(word in text for text in texts for word in _FORBIDDEN_WORDS):
            raise LLMOutputError(_WORDING_MESSAGE)

    def finding_labels(self, details: Mapping[str, object] | None) -> Mapping[str, str]:
        """寬限期中的項目顯示「寬限期中」，已見對應紀錄維持預設。"""
        entries = (details or {}).get("consultations")
        if not isinstance(entries, list):
            return {}
        # 舊版 details 只有 matched；歷史結果維持預設文字，不能因缺少新欄位而讀取失敗。
        return {
            item["item"]: _GRACE_LABEL
            for item in entries
            if isinstance(item, dict)
            and isinstance(item.get("item"), str)
            and item.get("status") == "IN_GRACE"
        }

    def _days(self) -> int:
        if self._followup_days is not None:
            return self._followup_days
        return get_settings().AUDIT_CONSULT_FOLLOWUP_DAYS

    def _consultations(self, ctx: AuditContext) -> list[SourceRecord]:
        return ctx.records_between(
            ctx.business_date - timedelta(days=self._days()),
            ctx.business_date,
            RawRecordCategory.CONSULTATION,
        )


def _consult_facts(record: SourceRecord, ctx: AuditContext, days: int) -> _ConsultationFacts:
    deadline = record.business_date + timedelta(days=days)
    return _ConsultationFacts(
        record_id=record.record_id,
        item=f"{record.business_date.isoformat()} {_note_department(record)}",
        deadline=deadline,
        is_due=deadline <= ctx.business_date,
        data_complete=record.business_date >= min(ctx.patient_dates),
    )


def _is_followup_note(record: SourceRecord) -> bool:
    return any(
        field.label == _CATEGORY_LABEL and field.value in FOLLOWUP_CATEGORIES
        for field in record.fields
    )


def _department(record: SourceRecord) -> str:
    return next(
        (field.value for field in record.fields if field.label == _CATEGORY_LABEL),
        _NO_DEPARTMENT,
    )


def _note_department(record: SourceRecord) -> str:
    """去掉科別中的醫師註記；去完為空時使用未提供科別文字。"""
    return _PHYSICIAN_NOTE_PATTERN.sub("", _department(record)).strip() or _NO_DEPARTMENT


def _consult_line(record: SourceRecord, fact: _ConsultationFacts) -> str:
    status = _DATA_COMPLETE if fact.data_complete else _DATA_INCOMPLETE
    due = "已到期" if fact.is_due else _GRACE_LABEL
    return (
        f"- record_id={record.record_id}｜item={fact.item}｜時間：{record.time_text}"
        f"｜科別：{_department(record)}｜到期日：{fact.deadline.isoformat()}"
        f"｜期限狀態：{due}｜期限內資料：{status}"
    )


def _check_coverage(output: R06Output, audit_input: AuditInput) -> None:
    expected = {
        record.record_id
        for record in audit_input.records
        if record.source == RawRecordCategory.CONSULTATION
    }
    answered = [item.record_id for item in output.consultations]
    if len(answered) != len(set(answered)) or set(answered) != expected:
        raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)


def _check_findings(
    output: R06Output, facts: Mapping[str, _ConsultationFacts], audit_input: AuditInput
) -> None:
    if len(output.findings) != len(output.consultations):
        raise LLMOutputError(_FINDING_MESSAGE)
    records = {record.record_id: record for record in audit_input.records}
    for match, finding in zip(output.consultations, output.findings, strict=True):
        fact = facts[match.record_id]
        if (fact.is_due and match.status == "IN_GRACE") or (
            not fact.is_due and match.status == "NOT_FOUND"
        ):
            raise LLMOutputError(_DEADLINE_MESSAGE)
        if not fact.data_complete and finding.verdict == "WARNING":
            raise LLMOutputError(_INCOMPLETE_WARNING_MESSAGE)
        expected = "PASS"
        if match.status == "NOT_FOUND":
            expected = "WARNING" if fact.data_complete else "NEEDS_REVIEW"
        if match.item != fact.item or finding.item != fact.item or finding.verdict != expected:
            raise LLMOutputError(_FINDING_MESSAGE)
        _check_evidence(match, finding, fact, records)


def _check_evidence(
    match: ConsultationMatch,
    finding: LlmFinding,
    fact: _ConsultationFacts,
    records: Mapping[str, SourceRecord],
) -> None:
    if not finding.evidence:
        raise LLMOutputError(_SOURCE_MESSAGE)
    consult = records[match.record_id]
    for evidence in finding.evidence:
        record = records.get(evidence.record_id)
        if match.status != "MATCHED":
            valid = evidence.record_id == match.record_id
        else:
            valid = (
                record is not None
                and record.source == RawRecordCategory.NURSING_PROGRESS_NOTE
                and _is_followup_note(record)
                and consult.business_date <= record.business_date <= fact.deadline
            )
        if not valid:
            raise LLMOutputError(_SOURCE_MESSAGE)


def _check_verdict(output: R06Output) -> None:
    expected = "PASS"
    verdicts = {finding.verdict for finding in output.findings}
    if "WARNING" in verdicts:
        expected = "WARNING"
    elif "NEEDS_REVIEW" in verdicts:
        expected = "NEEDS_REVIEW"
    if output.verdict != expected:
        raise LLMOutputError(_VERDICT_MESSAGE)
