"""R02 前後紀錄複製／一成不變／時效性。

LLM 逐筆比對今日護理過程紀錄與前 1 至 2 個資料日的紀錄，回傳相似紀錄、相似度與問題類型；
程式負責驗證 Evidence、補齊每筆紀錄的比對結果，並只用本模組的訊息模板組出提醒文字。
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import BUSINESS_TIMEZONE
from app.core.enums import Engine, Verdict
from app.core.exceptions import LLMOutputError
from app.schemas.audit import Evidence, IssueType, NoteSimilarity
from app.schemas.llm_structured import LLMRequest, LLMResult
from app.services.audit.base import (
    AuditContext,
    ProgressNoteRecord,
    RecordIndex,
    RuleResult,
    SourceRecord,
    StructuredLLM,
    index_records,
    validate_evidence,
)
from app.services.audit.source_records import build_source_records

logger = logging.getLogger(__name__)

R02_PROMPT_NAME: Final = "r02_copy_paste"
R02_PROMPT_VERSION: Final = "v1"
R02_PROMPT_ID: Final = f"{R02_PROMPT_NAME}/{R02_PROMPT_VERSION}"

# 必要要素（audit-rules.md）：由程式注入 prompt，不在模板內重複
R02_REQUIRED_ELEMENTS: Final[tuple[str, ...]] = (
    "相似比對：今日每筆護理過程紀錄與前 1 至 2 個資料日的護理過程紀錄比對，"
    "找出最相似的一筆並估計相似程度（0 至 100%）",
    "臨床資料是否變化：紀錄內容與前日相似，但生命徵象、檢驗或管路等臨床資料已有變化",
    "引用資料日期是否為當日：紀錄所描述的生命徵象、檢驗等數值，是否取自非當日的資料卻當作今日狀況",
)

# 訊息模板：提醒語氣，只代入時間、日期、紀錄 ID 與百分比，不放入模型回傳的文字
SIMILAR_TEMPLATE: Final = (
    "今日 {time} 紀錄（{record_id}）與 {similar_date} 紀錄（{similar_record_id}）相似 {percent}%"
)
CLINICAL_CHANGED_SUFFIX: Final = "，但生命徵象／檢驗／管路已有變化，請確認是否需更新"
OUTDATED_REFERENCE_TEMPLATE: Final = (
    "今日 {time} 紀錄（{record_id}）引用 {referenced_date} 的資料作為今日狀況"
)
SEGMENT_SEPARATOR: Final = "；"
CONFIRM_SUFFIX: Final = "，請確認"
NO_ISSUE_MESSAGE: Final = "未見與前日紀錄複製或引用非當日資料的情形"
NO_TODAY_NOTES_MESSAGE: Final = "今日未見護理過程紀錄，無法比對，請確認"
NO_PREVIOUS_NOTES_MESSAGE: Final = "前日未見護理過程紀錄，無法比對，請確認"
UNDETERMINED_MESSAGE: Final = "系統無法完成判定，請稍後重試或人工確認"
INVALID_PACKAGE_TEMPLATE: Final = "{date} 資料格式不符，無法判定，請確認"

_SIMILARITY_ISSUES: Final = frozenset({"copy", "unchanged", "clinical_changed"})
_PERCENT_STEP: Final = Decimal("0.1")
_TIME_FORMAT: Final = "%H:%M"


class R02EvidenceItem(BaseModel):
    """模型引用的原文片段。"""

    model_config = ConfigDict(extra="ignore")

    record_id: str
    field: str | None = None
    excerpt: str


class R02NoteJudgement(BaseModel):
    """今日一筆護理過程紀錄的比對結果。"""

    model_config = ConfigDict(extra="ignore")

    record_id: str
    similar_record_id: str | None
    similarity_percent: Annotated[float, Field(ge=0, le=100)] | None
    issue_types: list[IssueType]
    # outdated_reference 時，引用的非當日資料 record_id
    referenced_record_id: str | None = None


class R02LLMOutput(BaseModel):
    """R02 要求模型輸出的 JSON。"""

    model_config = ConfigDict(extra="ignore")

    verdict: Literal["PASS", "WARNING"]
    notes: list[R02NoteJudgement]
    evidence: list[R02EvidenceItem]


@dataclass(frozen=True)
class _NoteResult:
    similarity: NoteSimilarity
    segments: tuple[str, ...]


@dataclass(frozen=True)
class _Match:
    similar: SourceRecord | None
    percent: float | None
    referenced: SourceRecord | None
    issue_types: tuple[IssueType, ...]


class R02CopyPasteRule:
    """R02：今日紀錄與前日紀錄高度相似、臨床資料已變化，或引用非當日資料時提醒確認。"""

    code: ClassVar[str] = "R02"
    name: ClassVar[str] = "前後紀錄複製／一成不變／時效性"
    engine: ClassVar[Engine] = Engine.LLM

    def __init__(self, llm: StructuredLLM) -> None:
        """注入結構化 LLM 呼叫。

        Args:
            llm: 結構化 LLM 呼叫（正式環境為 gateway）。
        """
        self._llm = llm

    def applies_to(self, ctx: AuditContext) -> bool:
        """R02 每日適用；是否可稽核（入院首日）由 runner 依資料日判斷。"""
        return bool(ctx.business_date)

    async def evaluate(self, ctx: AuditContext) -> RuleResult:
        """檢查資料是否足以比對，再交給 LLM 判斷並驗證其輸出。

        `LLMNotConfiguredError` 不在此捕捉，交由 runner 回報未設定模型。
        """
        precheck = _precheck(ctx)
        if precheck is not None:
            return precheck
        records = build_source_records(ctx)
        request = LLMRequest(
            rule_code=self.code,
            prompt_name=R02_PROMPT_NAME,
            prompt_version=R02_PROMPT_VERSION,
            variables=_prompt_variables(ctx, records),
        )
        try:
            result = await self._llm(request, R02LLMOutput)
        except (LLMOutputError, TimeoutError, ConnectionError) as exc:
            logger.warning(
                "R02 無法完成判定：patient_key=%s error=%s", ctx.patient_key, type(exc).__name__
            )
            return RuleResult(
                verdict=Verdict.NEEDS_REVIEW,
                message=UNDETERMINED_MESSAGE,
                prompt_version=R02_PROMPT_ID,
            )
        return _judge(ctx, records, result)


def _precheck(ctx: AuditContext) -> RuleResult | None:
    """依序檢查 E9（資料格式）→ E6（今日紀錄）→ E6（前日紀錄）；都通過時回傳 `None`。"""
    if ctx.invalid_package_dates:
        latest = max(ctx.invalid_package_dates)
        message = INVALID_PACKAGE_TEMPLATE.format(date=_month_day(latest))
        return RuleResult(verdict=Verdict.NEEDS_REVIEW, message=message)
    today_notes = _today_notes(ctx)
    if not today_notes:
        return RuleResult(verdict=Verdict.NEEDS_REVIEW, message=NO_TODAY_NOTES_MESSAGE)
    if not _previous_note_ids(ctx):
        return RuleResult(
            verdict=Verdict.NEEDS_REVIEW,
            message=NO_PREVIOUS_NOTES_MESSAGE,
            note_similarities=tuple(_unmatched(note) for note in today_notes),
        )
    return None


def _today_notes(ctx: AuditContext) -> list[ProgressNoteRecord]:
    notes = [note for note in ctx.progress_notes if note.business_date == ctx.business_date]
    return sorted(notes, key=lambda note: note.recorded_at)


def _previous_note_ids(ctx: AuditContext) -> set[str]:
    return {
        note.record_id for note in ctx.progress_notes if note.business_date in ctx.previous_dates
    }


def _prompt_variables(ctx: AuditContext, records: Sequence[SourceRecord]) -> dict[str, object]:
    return {
        "required_elements": list(R02_REQUIRED_ELEMENTS),
        "business_date": ctx.business_date.isoformat(),
        "current_day": _day_block(ctx.business_date, records),
        "previous_days": [_day_block(day, records) for day in sorted(ctx.previous_dates)],
    }


def _day_block(day: date, records: Sequence[SourceRecord]) -> dict[str, object]:
    return {
        "date": day.isoformat(),
        "records": [
            {
                "source": record.source.value,
                "id": record.record_id,
                "date": record.business_date.isoformat(),
                "text": record.text,
                "note": record.note or "",
            }
            for record in records
            if record.business_date == day
        ],
    }


def _judge(
    ctx: AuditContext, records: Sequence[SourceRecord], result: LLMResult[R02LLMOutput]
) -> RuleResult:
    index = index_records(records)
    output = result.parsed
    evidence = tuple(validate_evidence(output.evidence, index))
    judgements = _usable_judgements(output.notes, ctx)
    notes = [
        _note_result(note, judgements.get(note.record_id), index) for note in _today_notes(ctx)
    ]
    segments = [segment for note in notes for segment in note.segments]
    verdict, message = _decide(output.verdict, segments, evidence)
    return RuleResult(
        verdict=verdict,
        message=message,
        evidence=evidence,
        note_similarities=tuple(note.similarity for note in notes),
        model=result.model,
        prompt_version=result.prompt_version,
        system_prompt_version=result.system_prompt_version,
    )


def _usable_judgements(
    judgements: Sequence[R02NoteJudgement], ctx: AuditContext
) -> dict[str, R02NoteJudgement]:
    """只採用今日紀錄、且相似紀錄為前日護理過程紀錄（或無）的項目；同一筆重複時取第一筆。"""
    today_ids = {note.record_id for note in _today_notes(ctx)}
    previous_ids = _previous_note_ids(ctx)
    usable: dict[str, R02NoteJudgement] = {}
    for judgement in judgements:
        similar_id = judgement.similar_record_id
        is_valid = judgement.record_id in today_ids and (
            similar_id is None or similar_id in previous_ids
        )
        if is_valid and judgement.record_id not in usable:
            usable[judgement.record_id] = judgement
    return usable


def _decide(
    llm_verdict: str, segments: Sequence[str], evidence: Sequence[Evidence]
) -> tuple[Verdict, str]:
    if llm_verdict == Verdict.PASS:
        return Verdict.PASS, NO_ISSUE_MESSAGE
    if not segments:
        return Verdict.NEEDS_REVIEW, UNDETERMINED_MESSAGE
    message = SEGMENT_SEPARATOR.join(segments) + CONFIRM_SUFFIX
    # WARNING 必須有驗證過的 Evidence，否則改為 NEEDS_REVIEW
    return (Verdict.WARNING if evidence else Verdict.NEEDS_REVIEW), message


def _note_result(
    note: ProgressNoteRecord, judgement: R02NoteJudgement | None, index: RecordIndex
) -> _NoteResult:
    if judgement is None:
        return _NoteResult(similarity=_unmatched(note), segments=())
    match = _match(judgement, index)
    similarity = NoteSimilarity(
        record_id=note.record_id,
        recorded_at=note.recorded_at,
        similar_record_id=match.similar.record_id if match.similar else None,
        similar_business_date=match.similar.business_date if match.similar else None,
        similarity_percent=match.percent,
        issue_types=list(match.issue_types),
    )
    return _NoteResult(similarity=similarity, segments=_segments(note, match))


def _match(judgement: R02NoteJudgement, index: RecordIndex) -> _Match:
    """整理模型的比對結果：相似紀錄與相似度需同時存在，引用資料需在送出的資料中。"""
    similar: SourceRecord | None = None
    if judgement.similar_record_id is not None and judgement.similarity_percent is not None:
        similar = _first(index, judgement.similar_record_id)
    referenced = _first(index, judgement.referenced_record_id)
    issue_types = tuple(dict.fromkeys(judgement.issue_types))
    if similar is None:
        issue_types = tuple(item for item in issue_types if item not in _SIMILARITY_ISSUES)
    if referenced is None:
        issue_types = tuple(item for item in issue_types if item != "outdated_reference")
    percent = _round_percent(judgement.similarity_percent) if similar is not None else None
    return _Match(similar, percent, referenced, issue_types)


def _segments(note: ProgressNoteRecord, match: _Match) -> tuple[str, ...]:
    segments: list[str] = []
    time = note.recorded_at.astimezone(BUSINESS_TIMEZONE).strftime(_TIME_FORMAT)
    if match.similar is not None and _SIMILARITY_ISSUES.intersection(match.issue_types):
        segment = SIMILAR_TEMPLATE.format(
            time=time,
            record_id=note.record_id,
            similar_date=_month_day(match.similar.business_date),
            similar_record_id=match.similar.record_id,
            percent=f"{match.percent:.1f}",
        )
        if "clinical_changed" in match.issue_types:
            segment += CLINICAL_CHANGED_SUFFIX
        segments.append(segment)
    if match.referenced is not None and "outdated_reference" in match.issue_types:
        segments.append(
            OUTDATED_REFERENCE_TEMPLATE.format(
                time=time,
                record_id=note.record_id,
                referenced_date=_month_day(match.referenced.business_date),
            )
        )
    return tuple(segments)


def _unmatched(note: ProgressNoteRecord) -> NoteSimilarity:
    return NoteSimilarity(
        record_id=note.record_id,
        recorded_at=note.recorded_at,
        similar_record_id=None,
        similar_business_date=None,
        similarity_percent=None,
        issue_types=[],
    )


def _first(index: RecordIndex, record_id: str | None) -> SourceRecord | None:
    if record_id is None:
        return None
    return next(iter(index.get(record_id, ())), None)


def _round_percent(value: float | None) -> float | None:
    """四捨五入到小數 1 位（ROUND_HALF_UP），例：97.65 → 97.7。"""
    if value is None:
        return None
    return float(Decimal(str(value)).quantize(_PERCENT_STEP, rounding=ROUND_HALF_UP))


def _month_day(day: date) -> str:
    """月不補零、日補兩位，例：`9/03`。"""
    return f"{day.month}/{day.day:02d}"
