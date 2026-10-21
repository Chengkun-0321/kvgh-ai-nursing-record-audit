"""稽核規則的共用介面、值物件與 Evidence 驗證 helper。

規則不存取 DB 或外部服務：所需資料由 `AuditContext`（不可變的值物件）提供，
LLM 由建構子注入的 `StructuredLLM` 呼叫，結果以 `RuleResult` 回傳，由 runner 統一寫入。
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import ClassVar, Final, Protocol

from pydantic import BaseModel

from app.core.enums import Engine, RecordSource, Verdict
from app.schemas.audit import Evidence, NoteSimilarity
from app.schemas.llm_structured import LLMRequest, LLMResult


class StructuredLLM(Protocol):
    """結構化 LLM 呼叫（正式環境為 `gateway.complete_structured`，測試時可替換）。"""

    async def __call__[T: BaseModel](
        self, request: LLMRequest, output_schema: type[T]
    ) -> LLMResult[T]:
        """渲染 prompt、呼叫模型並以 `output_schema` 驗證輸出。"""


@dataclass(frozen=True)
class ProgressNoteRecord:
    """護理過程紀錄。"""

    record_id: str
    business_date: date
    recorded_at: datetime
    title_category: str
    title: str
    content: str


@dataclass(frozen=True)
class VitalSignRecord:
    """生命徵象。"""

    record_id: str
    business_date: date
    measured_at: datetime
    body_temperature: float | None
    temperature_site: str | None
    pulse: int | None
    respiration: int | None
    sbp: int | None
    dbp: int | None
    spo2: int | None
    oxygen_therapy: str | None


@dataclass(frozen=True)
class LabResultRecord:
    """檢驗結果。"""

    record_id: str
    business_date: date
    order_name: str
    item: str
    value: str
    unit: str | None
    reference_range: str | None
    abnormal_flag: str | None
    collected_at: datetime


@dataclass(frozen=True)
class TubeRecord:
    """管路在某一天的現況。"""

    tube_id: str
    business_date: date
    tube_type: str
    site: str
    size: str | None
    inserted_on: date | None
    removed_on: date | None
    fixation: str | None
    appearance: str | None


@dataclass(frozen=True)
class AuditContext:
    """一位病患、一個業務日的稽核所需資料（同一住院、比對範圍內的日期）。"""

    patient_key: str
    admission_id: str
    business_date: date
    # 比對範圍內、早於當日的資料日（由新到舊）
    previous_dates: tuple[date, ...]
    progress_notes: tuple[ProgressNoteRecord, ...] = ()
    vital_signs: tuple[VitalSignRecord, ...] = ()
    lab_results: tuple[LabResultRecord, ...] = ()
    tubes: tuple[TubeRecord, ...] = ()
    # 比對範圍內該病患檔驗證失敗的日期（E9）
    invalid_package_dates: tuple[date, ...] = ()


@dataclass(frozen=True)
class RuleResult:
    """規則的判定結果；模型資訊只有實際呼叫 LLM 時才有。"""

    verdict: Verdict
    message: str
    evidence: tuple[Evidence, ...] = ()
    note_similarities: tuple[NoteSimilarity, ...] = ()
    model: str | None = None
    prompt_version: str | None = None
    system_prompt_version: int | None = None


class AuditRule(Protocol):
    """稽核規則（Strategy）：由 `RULE_REGISTRY` 依代碼取得類別，以注入的 LLM 建立。"""

    code: ClassVar[str]
    name: ClassVar[str]
    engine: ClassVar[Engine]

    def __init__(self, llm: StructuredLLM) -> None:
        """注入結構化 LLM 呼叫。"""

    def applies_to(self, ctx: AuditContext) -> bool:
        """此規則是否適用於該 context。"""

    async def evaluate(self, ctx: AuditContext) -> RuleResult:
        """產生判定結果（無副作用）。"""


@dataclass(frozen=True)
class SourceRecord:
    """送給 LLM 的一筆資料與其原文 `text`；Evidence 也以同一段 `text` 驗證。"""

    source: RecordSource
    record_id: str
    business_date: date
    # Evidence 的時間：紀錄 recorded_at、生命徵象 measured_at、檢驗 collected_at；管路沒有
    recorded_at: datetime | None
    text: str
    # 放在 prompt 中的補充說明（例如紀錄時間與標籤）；不參與 Evidence 比對
    note: str | None = None


class EvidenceCandidate(Protocol):
    """LLM 回傳的一筆 Evidence（尚未驗證）。"""

    @property
    def record_id(self) -> str:
        """引用的紀錄 ID。"""

    @property
    def field(self) -> str | None:
        """引用的欄位。"""

    @property
    def excerpt(self) -> str:
        """原文片段。"""


# LLM 沒有指明欄位時的預設：護理過程紀錄引用的是內文
DEFAULT_EVIDENCE_FIELDS: Final[Mapping[RecordSource, str]] = MappingProxyType(
    {RecordSource.NURSING_PROGRESS_NOTE: "content"}
)

RecordIndex = Mapping[str, Sequence[SourceRecord]]


def strip_whitespace(text: str) -> str:
    """去除所有空白（含全形空白與換行），用於原文片段比對。"""
    return "".join(text.split())


def index_records(records: Sequence[SourceRecord]) -> dict[str, list[SourceRecord]]:
    """依 ID 建立索引；管路每天都會出現，同一 ID 可能對應多天的資料。"""
    index: dict[str, list[SourceRecord]] = {}
    for record in records:
        index.setdefault(record.record_id, []).append(record)
    return index


def find_excerpt_source(candidate: EvidenceCandidate, index: RecordIndex) -> SourceRecord | None:
    """找出原文中含有該片段的資料；ID 不在送出的資料中，或片段找不到時回傳 `None`。"""
    excerpt = strip_whitespace(candidate.excerpt)
    if not excerpt:
        return None
    return next(
        (
            record
            for record in index.get(candidate.record_id, ())
            if excerpt in strip_whitespace(record.text)
        ),
        None,
    )


def validate_evidence(
    candidates: Sequence[EvidenceCandidate], index: RecordIndex
) -> list[Evidence]:
    """只保留能在原文找到的 Evidence（hallucination guard）。

    來源與時間由程式依資料類型填入，不採用 LLM 的值；欄位未給時套用預設值。

    Args:
        candidates: LLM 回傳的 Evidence。
        index: 送給 LLM 的資料（`index_records` 產生）。

    Returns:
        驗證通過的 Evidence，順序與輸入相同。
    """
    evidence: list[Evidence] = []
    for candidate in candidates:
        record = find_excerpt_source(candidate, index)
        if record is None:
            continue
        evidence.append(
            Evidence(
                source=record.source.value,
                record_id=record.record_id,
                field=candidate.field or DEFAULT_EVIDENCE_FIELDS.get(record.source),
                recorded_at=record.recorded_at,
                excerpt=candidate.excerpt,
            )
        )
    return evidence
