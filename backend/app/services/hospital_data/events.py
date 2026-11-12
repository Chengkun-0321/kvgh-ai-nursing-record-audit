"""把院方病人檔的各區塊轉成時間軸紀錄（檢驗報告另見 `labs.py`）。

各區塊的欄位對應寫成宣告式的 `SECTION_SPECS`：時間、標籤、標題、內文各取哪個欄位，
其餘欄位依院方原順序成為「項目：結果」。院方新增欄位時會自動出現在畫面上，不會被丟掉。
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Final

from app.core.enums import AbnormalFlag, RawRecordCategory
from app.schemas.hospital_data.raw import RawPatientFile, RawRecord
from app.schemas.hospital_data.timeline import (
    LabeledValueRead,
    LabResultRead,
    TimelineEventRead,
)
from app.services.hospital_data.times import RecordTime, parse_record_time

# 畫面上的類別名稱；順序即類別篩選與筆數統計的顯示順序
CATEGORY_LABELS: Final[dict[RawRecordCategory, str]] = {
    RawRecordCategory.NURSING_PROGRESS_NOTE: "護理記錄",
    RawRecordCategory.VITAL_SIGN: "生命徵象",
    RawRecordCategory.LAB_RESULT: "檢驗報告",
    RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT: "每日身評",
    RawRecordCategory.ADMISSION_ASSESSMENT: "入院身體評估",
    RawRecordCategory.ADMISSION_COURSE: "入院經過",
    RawRecordCategory.GCS: "GCS",
    RawRecordCategory.MEDICATION_ORDER: "用藥",
    RawRecordCategory.EXAMINATION: "檢查",
    RawRecordCategory.CONSULTATION: "會診",
    RawRecordCategory.BED_TRANSFER: "轉床",
}

BASIC_INFO_SECTION: Final = "病人基本資料"
ADMITTED_AT_FIELD: Final = "入院時間"
_ADMISSION_COURSE_SECTION: Final = "入院經過"
_EVENT_ID_LENGTH: Final = 16


@dataclass(frozen=True)
class SectionSpec:
    """院方一個區塊對應到時間軸紀錄的方式。"""

    category: RawRecordCategory
    section_name: str
    time_field: str
    tag_field: str | None = None
    title_field: str | None = None
    text_field: str | None = None


SECTION_SPECS: Final = (
    SectionSpec(RawRecordCategory.NURSING_PROGRESS_NOTE, "護理記錄", "日期", "類別", None, "內容"),
    SectionSpec(RawRecordCategory.VITAL_SIGN, "生命徵象", "日期"),
    SectionSpec(RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT, "每日身評", "身評時間"),
    SectionSpec(RawRecordCategory.ADMISSION_ASSESSMENT, "入院身體評估", "評估日期時間"),
    SectionSpec(RawRecordCategory.GCS, "GCS", "測量時間"),
    SectionSpec(RawRecordCategory.MEDICATION_ORDER, "用藥", "日期", None, "藥名"),
    SectionSpec(RawRecordCategory.EXAMINATION, "檢查", "日期", "狀態", "項目", "內容"),
    SectionSpec(RawRecordCategory.CONSULTATION, "會診", "日期", "科別"),
    SectionSpec(RawRecordCategory.BED_TRANSFER, "轉床資料", "操作日期"),
)


@dataclass(frozen=True)
class EventContent:
    """組成一筆時間軸紀錄的內容（不含資料日期）；相同內容視為同一筆紀錄。"""

    category: RawRecordCategory
    time: RecordTime
    tag: str | None = None
    title: str | None = None
    text: str | None = None
    fields: tuple[LabeledValueRead, ...] = ()
    lab_results: tuple[LabResultRead, ...] = ()


def build_section_contents(patient_file: RawPatientFile) -> list[EventContent]:
    """把病人檔中檢驗報告以外的所有區塊轉成時間軸紀錄的內容（與資料日期無關）。"""
    contents = [
        _content_from_record(spec, record)
        for spec in SECTION_SPECS
        for record in patient_file.records(spec.section_name)
    ]
    admission_course = _admission_course_content(patient_file)
    if admission_course is not None:
        contents.append(admission_course)
    return contents


def build_event(content: EventContent, business_date: date) -> TimelineEventRead:
    """由內容組出時間軸紀錄；`event_id` 只由內容決定，跨日重複的紀錄會得到相同 ID。"""
    return build_identified_event(content_event_id(content), content, business_date)


def build_identified_event(
    event_id: str, content: EventContent, business_date: date
) -> TimelineEventRead:
    """以已算好的 `event_id`（見 `content_event_id`）組出時間軸紀錄。"""
    flags = [result.abnormal_flag for result in content.lab_results]
    return TimelineEventRead(
        event_id=event_id,
        category=content.category,
        category_label=CATEGORY_LABELS[content.category],
        business_date=business_date,
        time_text=content.time.text,
        occurred_at=content.time.occurred_at,
        is_date_only=content.time.is_date_only,
        tag=content.tag,
        title=content.title,
        text=content.text,
        # 內容可能來自快取，而 Pydantic 不會複製傳入的 model；各複製一份，修改回應才不會改到快取
        fields=[field.model_copy() for field in content.fields],
        lab_results=[result.model_copy() for result in content.lab_results],
        abnormal_high_count=flags.count(AbnormalFlag.HIGH),
        abnormal_low_count=flags.count(AbnormalFlag.LOW),
    )


def content_event_id(content: EventContent) -> str:
    """由內容（不含資料日期）算出的紀錄 ID；內容相同即 ID 相同。"""
    payload = json.dumps(_content_payload(content), ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:_EVENT_ID_LENGTH]


def admitted_at_text(patient_file: RawPatientFile) -> str | None:
    """病人基本資料中的入院時間原文。"""
    return patient_file.first_record(BASIC_INFO_SECTION).get(ADMITTED_AT_FIELD)


def _content_from_record(spec: SectionSpec, record: RawRecord) -> EventContent:
    used_fields = {spec.time_field, spec.tag_field, spec.title_field, spec.text_field}
    return EventContent(
        category=spec.category,
        time=parse_record_time(record.get(spec.time_field, "")),
        tag=_optional_field(record, spec.tag_field),
        title=_optional_field(record, spec.title_field),
        text=_optional_field(record, spec.text_field),
        fields=_labeled_values(record, exclude=used_fields),
    )


def _admission_course_content(patient_file: RawPatientFile) -> EventContent | None:
    # 入院經過沒有自己的時間，掛在入院時間上
    paragraphs = patient_file.texts(_ADMISSION_COURSE_SECTION)
    if not paragraphs:
        return None
    return EventContent(
        category=RawRecordCategory.ADMISSION_COURSE,
        time=parse_record_time(admitted_at_text(patient_file) or ""),
        text="\n\n".join(paragraphs),
    )


def _optional_field(record: RawRecord, field_name: str | None) -> str | None:
    if field_name is None:
        return None
    return record.get(field_name)


def _labeled_values(record: RawRecord, exclude: set[str | None]) -> tuple[LabeledValueRead, ...]:
    return tuple(
        LabeledValueRead(label=label, value=value)
        for label, value in record.items()
        if label not in exclude
    )


def _content_payload(content: EventContent) -> dict[str, object]:
    return {
        "category": content.category.value,
        "time": content.time.text,
        "tag": content.tag,
        "title": content.title,
        "text": content.text,
        "fields": _dump_all(content.fields),
        "lab_results": _dump_all(content.lab_results),
    }


def _dump_all(items: Sequence[LabeledValueRead | LabResultRead]) -> list[dict[str, object]]:
    return [item.model_dump(mode="json") for item in items]
