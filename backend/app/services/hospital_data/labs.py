"""檢驗報告：院方每筆是「日期＋一個項目（動態鍵）＋範圍＋異常值」，這裡拆成結構化結果。

跨日合併時先以「採檢時間＋項目＋結果＋範圍＋異常標記」去重，再依採檢時間分組；
同一次採檢分散在不同天的檔案時，仍會合成一張卡片。檢驗矩陣中同一格有多個不同結果時全部保留。
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Final

from app.core.enums import AbnormalFlag, RawRecordCategory
from app.schemas.hospital_data.raw import RawPatientFile, RawRecord
from app.schemas.hospital_data.timeline import (
    LabMatrixColumnRead,
    LabMatrixRowRead,
    LabMatrixValueRead,
    LabResultRead,
    TimelineEventRead,
)
from app.services.hospital_data.events import EventContent, build_event
from app.services.hospital_data.times import RecordTime, parse_record_time

LAB_SECTION: Final = "檢驗報告"
_TIME_FIELD: Final = "日期"
_RANGE_FIELD: Final = "範圍"
_ABNORMAL_FIELD: Final = "異常值"
_META_FIELDS: Final = frozenset({_TIME_FIELD, _RANGE_FIELD, _ABNORMAL_FIELD})
# 院方偶有項目名稱為空字串的紀錄；照原樣保留，只給畫面一個可讀的名稱
UNNAMED_ITEM_LABEL: Final = "（院方未提供項目名）"
_NORMAL_TEXT: Final = "No"
_ABNORMAL_PREFIX: Final = "Yes"


@dataclass(frozen=True)
class LabRow:
    """一個檢驗項目的一次結果，附來源資料日期。"""

    time: RecordTime
    business_date: date
    result: LabResultRead

    @property
    def dedupe_key(self) -> tuple[str, str, str, str | None, AbnormalFlag | None]:
        """去重鍵：不含資料日期，同一結果出現在多天檔案時視為同一筆（異常標記不同則不合併）。"""
        result = self.result
        return (
            self.time.text,
            result.item,
            result.value,
            result.reference_range,
            result.abnormal_flag,
        )


def extract_lab_rows(patient_file: RawPatientFile, business_date: date) -> list[LabRow]:
    """取出病人檔的所有檢驗結果。"""
    return [
        LabRow(
            time=parse_record_time(record.get(_TIME_FIELD, "")),
            business_date=business_date,
            result=result,
        )
        for record in patient_file.records(LAB_SECTION)
        for result in _parse_lab_record(record)
    ]


def merge_lab_rows(rows: Iterable[LabRow]) -> list[LabRow]:
    """去除跨日重複的結果，保留最早的資料日期；依採檢時間排序。"""
    merged: dict[tuple[str, str, str, str | None, AbnormalFlag | None], LabRow] = {}
    for row in sorted(rows, key=lambda r: r.business_date):
        merged.setdefault(row.dedupe_key, row)
    return sorted(merged.values(), key=_row_sort_key)


def build_lab_events(rows: list[LabRow]) -> list[TimelineEventRead]:
    """同一採檢時間的結果合成一筆時間軸紀錄。"""
    return [_lab_event(group) for group in _group_by_time(rows).values()]


def build_lab_matrix(
    rows: list[LabRow],
) -> tuple[list[LabMatrixColumnRead], list[LabMatrixRowRead]]:
    """組出項目 × 採檢時間矩陣；列依項目第一次出現的順序，同組檢驗會排在一起。"""
    groups = _group_by_time(rows)
    columns = [
        LabMatrixColumnRead(time_text=group[0].time.text, occurred_at=group[0].time.occurred_at)
        for group in groups.values()
    ]
    column_index = {time_text: index for index, time_text in enumerate(groups)}
    matrix: dict[str, LabMatrixRowRead] = {}
    for row in rows:
        matrix_row = matrix.setdefault(row.result.item, _empty_matrix_row(row, len(columns)))
        _add_to_row(matrix_row, row, column_index[row.time.text])
    return columns, list(matrix.values())


def _add_to_row(matrix_row: LabMatrixRowRead, row: LabRow, column: int) -> None:
    value = LabMatrixValueRead(value=row.result.value, abnormal_flag=row.result.abnormal_flag)
    matrix_row.cells[column].append(value)
    reference_range = row.result.reference_range
    if reference_range and reference_range not in matrix_row.reference_ranges:
        matrix_row.reference_ranges.append(reference_range)


def _parse_lab_record(record: RawRecord) -> list[LabResultRead]:
    items = [(key, value) for key, value in record.items() if key not in _META_FIELDS]
    # 範圍與異常值只在一筆只有一個項目時才能確定屬於哪個項目
    is_single_item = len(items) == 1
    return [
        LabResultRead(
            item=key or UNNAMED_ITEM_LABEL,
            value=value,
            reference_range=record.get(_RANGE_FIELD) if is_single_item else None,
            abnormal_flag=parse_abnormal_flag(record.get(_ABNORMAL_FIELD))
            if is_single_item
            else None,
        )
        for key, value in items
    ]


def parse_abnormal_flag(text: str | None) -> AbnormalFlag | None:
    """院方「異常值」：`No`、`Yes (↑)`、`Yes (↓)`；其他寫法回傳 `None`（不猜測）。"""
    if text is None:
        return None
    stripped = text.strip()
    if stripped == _NORMAL_TEXT:
        return AbnormalFlag.NORMAL
    if not stripped.startswith(_ABNORMAL_PREFIX):
        return None
    return _abnormal_direction(stripped)


def _abnormal_direction(text: str) -> AbnormalFlag:
    if "↑" in text:
        return AbnormalFlag.HIGH
    return AbnormalFlag.LOW if "↓" in text else AbnormalFlag.ABNORMAL


def _group_by_time(rows: list[LabRow]) -> dict[str, list[LabRow]]:
    groups: dict[str, list[LabRow]] = {}
    for row in rows:
        groups.setdefault(row.time.text, []).append(row)
    return groups


def _lab_event(group: list[LabRow]) -> TimelineEventRead:
    content = EventContent(
        category=RawRecordCategory.LAB_RESULT,
        time=group[0].time,
        title=f"{len(group)} 項",
        lab_results=tuple(row.result for row in group),
    )
    return build_event(content, min(row.business_date for row in group))


def _empty_matrix_row(row: LabRow, column_count: int) -> LabMatrixRowRead:
    return LabMatrixRowRead(
        item=row.result.item, reference_ranges=[], cells=[[] for _ in range(column_count)]
    )


def _row_sort_key(row: LabRow) -> tuple[bool, str]:
    # 無法解析的時間排在最後，其餘依原文排序（院方格式固定為 YYYY-MM-DD HH:MM）
    return (row.time.occurred_at is None, row.time.text)
