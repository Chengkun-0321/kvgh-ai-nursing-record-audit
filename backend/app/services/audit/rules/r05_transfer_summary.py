"""R05 轉入／轉出摘要完整性（事件規則，預留模組：目前不判斷）。

院方資料目前沒有「轉出摘要」「轉入摘要」，轉床紀錄只有病房內換床。因此 `check_availability`
一律回傳 DATA_UNAVAILABLE，流程不呼叫 LLM，只寫入一筆 DATA_UNAVAILABLE 的紀錄。

`build_input` 已依預期的資料形狀實作（當日轉床紀錄、類別為轉出／轉入摘要的護理紀錄、
當日身評的管路欄位），目前不會被呼叫到，以虛構資料測試通過。

資料到位後要改的地方：
1. `check_availability`：改為依院方資料判斷。有轉床事件且摘要齊備 → AVAILABLE；
   當日無轉床事件 → NOT_APPLICABLE；缺摘要的情形仍以 AVAILABLE 進入 LLM，由 prompt 判斷「未見」。
2. `_summaries`、`_tube_fields`：院方格式不同時只改篩選條件（類別值、欄位標籤）。
3. 必要要素與範本參考：改本模組的常數，與 `prompts/r05_transfer_summary/v1.j2` 同步。

待院方確認：轉床紀錄能否判斷轉出或轉入方向；身評管路欄位的標籤名稱。
"""

from typing import ClassVar, Final, Literal

from pydantic import BaseModel, Field

from app.core.enums import AuditCycle, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceField, SourceRecord
from app.services.audit.rules.base import AuditInput, Availability, data_unavailable

OUTGOING_SUMMARY: Final = "轉出摘要"
INCOMING_SUMMARY: Final = "轉入摘要"
SummaryKind = Literal["轉出摘要", "轉入摘要"]

# 必要要素（依摘要類型），由程式注入 prompt；院方尚未確認前以此清單為準
REQUIRED_ELEMENTS: Final[dict[str, tuple[str, ...]]] = {
    OUTGOING_SUMMARY: (
        "住院期間重要檢查",
        "治療結果",
        "目前病況",
        "管路",
        "傷口",
        "健康問題",
        "轉出原因",
    ),
    INCOMING_SUMMARY: ("意識", "呼吸", "身體活動", "管路", "皮膚狀況", "現存健康問題"),
}
# 院方範本標示為「視病人狀況」的要素：只有紀錄顯示病人有該狀況時才要求
CONDITIONAL_ELEMENTS: Final = frozenset({"傷口"})
# 院方（09-24）提供的轉出摘要範本，僅作參考寫法，不要求逐字相同
OUTGOING_TEMPLATE: Final = (
    "入院經過＜＞住院期間因＜＞行＜＞檢查，報告為＜＞。因＜＞給予＜＞治療。"
    "目前 GCS＜＞生命徵象＜＞。＜＞氧氣使用，血氧＜＞%。＜＞管路留置。"
    "＜＞傷口，換藥方式為＜＞，每日＜＞次。＜＞部位壓傷＜＞級。目前健康問題為＜＞。"
    "因＜＞原因，故轉＜＞病房續治療，已向＜＞家屬說明轉床原因，並填妥＜＞同意書。"
    "攜帶高貴藥物＜＞及貴重物品＜＞"
)
# 護理紀錄中「類別」欄位的標籤（與 services/audit/records.py 的合成欄位名稱一致）
TAG_LABEL: Final = "類別"
# 身評欄位標籤含此字即視為管路欄位（院方標籤待確認）
TUBE_KEYWORD: Final = "管路"
_REASON: Final = (
    "院方尚未提供所需資料：院方資料沒有「轉出摘要」「轉入摘要」，"
    "轉床紀錄只有病房內換床，本項目目前無法判斷。"
)
_INVALID_OUTPUT_MESSAGE: Final = "模型輸出的摘要類型或項目不在必要要素清單內，無法判定"


class ElementMention(BaseModel):
    """一個摘要類型中的必要要素是否有被提及。"""

    summary_kind: SummaryKind
    element: str
    mentioned: bool


class R05Output(RuleOutput):
    """R05 的專屬欄位：各必要要素是否提及（存入結果的 details）。"""

    elements: list[ElementMention] = Field(default_factory=list)


class R05TransferSummary:
    """R05 規則；目前預留，`check_availability` 一律回傳 DATA_UNAVAILABLE。"""

    code: ClassVar[str] = "R05"
    name: ClassVar[str] = "轉入／轉出摘要完整性"
    description: ClassVar[str] = (
        "轉入或轉出時，摘要是否包含必要項目。院方目前沒有轉出／轉入摘要，本項不判斷。"
    )
    cycle: ClassVar[AuditCycle] = AuditCycle.EVENT
    prompt_name: ClassVar[str] = "r05_transfer_summary"
    prompt_version: ClassVar[int] = 1
    output_schema: ClassVar[type[RuleOutput]] = R05Output

    def check_availability(self, ctx: AuditContext) -> Availability:
        return data_unavailable(_REASON)

    def build_input(self, ctx: AuditContext) -> AuditInput:
        day = ctx.business_date
        transfers = ctx.records_on(day, RawRecordCategory.BED_TRANSFER.value)
        nursing = ctx.records_on(day, RawRecordCategory.NURSING_PROGRESS_NOTE.value)
        summaries = {kind: _with_tag(nursing, kind) for kind in REQUIRED_ELEMENTS}
        tube_records = [
            record
            for record in ctx.records_on(day, RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT.value)
            if _tube_fields(record)
        ]
        variables = {
            "transfer_status": _count_status(transfers, "本日有轉床紀錄", "本日沒有轉床紀錄"),
            "outgoing_status": _count_status(
                summaries[OUTGOING_SUMMARY], "有紀錄", "未見紀錄或院方未提供"
            ),
            "incoming_status": _count_status(
                summaries[INCOMING_SUMMARY], "有紀錄", "未見紀錄或院方未提供"
            ),
            "required_elements_block": _required_elements_lines(),
            "tube_block": _tube_lines(tube_records),
            "outgoing_template": OUTGOING_TEMPLATE,
        }
        records = (
            *transfers,
            *summaries[OUTGOING_SUMMARY],
            *summaries[INCOMING_SUMMARY],
            *tube_records,
        )
        return AuditInput(variables=variables, records=records)

    def validate_output(self, output: RuleOutput, audit_input: AuditInput) -> None:
        if not isinstance(output, R05Output):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        if any(_pair(m) not in _valid_pairs() for m in output.elements):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)
        if any(finding.item not in _allowed_items() for finding in output.findings):
            raise LLMOutputError(_INVALID_OUTPUT_MESSAGE)


def _pair(mention: ElementMention) -> tuple[str, str]:
    return (mention.summary_kind, mention.element)


def _valid_pairs() -> frozenset[tuple[str, str]]:
    return frozenset(
        (kind, element) for kind, elements in REQUIRED_ELEMENTS.items() for element in elements
    )


def _allowed_items() -> frozenset[str]:
    """finding 的 item 可用的名稱：摘要類型本身，或「摘要類型：要素」。"""
    labels = {f"{kind}：{element}" for kind, element in _valid_pairs()}
    return frozenset({*REQUIRED_ELEMENTS, *labels})


def _with_tag(records: list[SourceRecord], tag: str) -> list[SourceRecord]:
    return [record for record in records if _field_value(record, TAG_LABEL) == tag]


def _field_value(record: SourceRecord, label: str) -> str | None:
    return next((field.value for field in record.fields if field.label == label), None)


def _tube_fields(record: SourceRecord) -> list[SourceField]:
    return [field for field in record.fields if TUBE_KEYWORD in field.label]


def _count_status(records: list[SourceRecord], found: str, none: str) -> str:
    return f"{found}（{len(records)} 筆）" if records else none


def _required_elements_lines() -> str:
    lines = []
    for kind, elements in REQUIRED_ELEMENTS.items():
        names = "、".join(_element_text(element) for element in elements)
        lines.append(f"- {kind}：{names}")
    return "\n".join(lines)


def _element_text(element: str) -> str:
    return f"{element}（視病人狀況）" if element in CONDITIONAL_ELEMENTS else element


def _tube_lines(records: list[SourceRecord]) -> str:
    lines = [
        f"- {record.business_date.isoformat()} {field.label}：{field.value}"
        for record in records
        for field in _tube_fields(record)
    ]
    return "\n".join(lines) if lines else "本日身評未見管路資料"
