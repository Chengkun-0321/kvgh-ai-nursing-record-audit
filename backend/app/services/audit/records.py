"""院方紀錄 → 可引用的 `SourceRecord`，以及渲染成 prompt 用的 `<record>` 區塊。

record_id 沿用時間軸的 `event_id`（內容雜湊）：院方資料沒有紀錄 ID，相同內容跨日會得到相同 ID，
Evidence 的 record_id 因此可以追回原文。
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Final

from app.core.enums import AbnormalFlag
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.hospital_data.timeline import LabResultRead, TimelineEventRead
from app.services.hospital_data.timeline import event_day

CHECKLIST_SOURCE: Final = "work_checklist"
_CHECKLIST_LABEL: Final = "工作清單"
# 院方「異常值」欄的標記 → 給 LLM 與畫面看的文字；正常或未提供時不標
_ABNORMAL_NOTES: Final[dict[AbnormalFlag, str]] = {
    AbnormalFlag.HIGH: "院方標記：偏高",
    AbnormalFlag.LOW: "院方標記：偏低",
    AbnormalFlag.ABNORMAL: "院方標記：異常",
}
_CONTINUATION_INDENT: Final = "\n  "
_CHECKLIST_ID_LENGTH: Final = 16
_NO_RECORDS_TEXT: Final = "（本次沒有可引用的紀錄）"


@dataclass(frozen=True)
class SourceField:
    """紀錄中的一個欄位（標籤＋原文值）。

    `note` 是院方對該值的標記（目前只有檢驗的異常標記），不屬於原文，不參與 Evidence 核對。
    """

    label: str
    value: str
    note: str | None = None


@dataclass(frozen=True)
class SourceRecord:
    """可被 LLM 引用的一筆紀錄。

    `source` 為 `RawRecordCategory` 的值，或合成來源（如 `work_checklist`）；
    `source_label` 是畫面顯示用的繁中名稱，未提供時以 `source` 代替。
    `raw_text` 是 Evidence 核對時的原文，excerpt 必須能在其中找到。
    """

    record_id: str
    source: str
    business_date: date
    time_text: str
    recorded_at: datetime | None
    fields: tuple[SourceField, ...]
    source_label: str = ""

    @property
    def raw_text(self) -> str:
        """所有欄位值合併後的原文。"""
        return "\n".join(field.value for field in self.fields)


def from_timeline_event(event: TimelineEventRead) -> SourceRecord:
    """時間軸紀錄 → SourceRecord；歸日依紀錄本身的時間。"""
    return SourceRecord(
        record_id=event.event_id,
        source=event.category.value,
        business_date=event_day(event),
        time_text=event.time_text,
        recorded_at=event.occurred_at,
        fields=_event_fields(event),
        source_label=event.category_label,
    )


def from_checklist(checklist: WorkChecklistRead, business_date: date) -> SourceRecord:
    """工作清單 → 合成的 SourceRecord，讓 R03 的發現也能附 Evidence。

    record_id 由內容決定：同樣的清單得到同一個 ID。
    """
    fields = tuple(SourceField(item.label, item.value) for item in checklist.items)
    payload = json.dumps([[field.label, field.value] for field in fields], ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:_CHECKLIST_ID_LENGTH]
    return SourceRecord(
        record_id=f"{CHECKLIST_SOURCE}-{digest}",
        source=CHECKLIST_SOURCE,
        business_date=business_date,
        time_text="",
        recorded_at=None,
        fields=fields,
        source_label=_CHECKLIST_LABEL,
    )


def abnormal_only(record: SourceRecord) -> SourceRecord | None:
    """只保留院方標記為異常的欄位（檢驗用）；沒有異常欄位時回傳 None。

    record_id 不變，Evidence 仍可指回原紀錄。
    """
    flagged = tuple(field for field in record.fields if field.note is not None)
    return replace(record, fields=flagged) if flagged else None


def render_records_block(records: Iterable[SourceRecord]) -> str:
    """渲染成 prompt 的紀錄區塊；每筆以 `<record source= id= date=>` 標示來源與 record_id。"""
    rendered = [_render_one(record) for record in records]
    return "\n".join(rendered) if rendered else _NO_RECORDS_TEXT


def _render_one(record: SourceRecord) -> str:
    header = (
        f'<record source="{record.source}" id="{record.record_id}" '
        f'date="{record.business_date.isoformat()}" time="{record.time_text}">'
    )
    body = "\n".join(_render_field(field) for field in record.fields)
    return f"{header}\n{body}\n</record>"


def _render_field(field: SourceField) -> str:
    """多行的欄位值把續行縮排，讓 LLM 看得出它們屬於同一個欄位。"""
    lines = field.value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    value = _CONTINUATION_INDENT.join(lines)
    note = f"（{field.note}）" if field.note else ""
    return f"{field.label}：{value}{note}"


def _event_fields(event: TimelineEventRead) -> tuple[SourceField, ...]:
    return (
        *_named("類別", event.tag),
        *_named("標題", event.title),
        *_named("內容", event.text),
        *(SourceField(field.label, field.value) for field in event.fields),
        *(_lab_field(result) for result in event.lab_results),
    )


def _lab_field(result: LabResultRead) -> SourceField:
    note = _ABNORMAL_NOTES.get(result.abnormal_flag) if result.abnormal_flag else None
    return SourceField(result.item, result.value, note)


def _named(label: str, value: str | None) -> tuple[SourceField, ...]:
    return (SourceField(label, value),) if value else ()
