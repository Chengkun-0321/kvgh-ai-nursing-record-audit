"""合併一位病人各日期的資料檔，組出時間軸與檢驗矩陣（同步函式，由 service 放到 thread 執行）。

院方每天的檔案只含當天紀錄，但「檢查」會帶歷史紀錄，所以合併時以內容去重。
每個病人檔轉出的內容會快取（見 `_file_records`），合併、排序與組成回應物件則每次重做。
"""

from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
from typing import Final

from app.core.enums import RawRecordCategory
from app.core.exceptions import InvalidInputError
from app.schemas.hospital_data.raw import RawPatientFile
from app.schemas.hospital_data.timeline import (
    LabMatrixRead,
    PatientTimelineRead,
    TimelineDayRead,
    TimelineEventRead,
)
from app.services.hospital_data.events import (
    CATEGORY_LABELS,
    EventContent,
    build_identified_event,
    build_section_contents,
    content_event_id,
)
from app.services.hospital_data.index import PatientHistory
from app.services.hospital_data.labs import (
    LabRow,
    build_lab_events,
    build_lab_matrix,
    count_lab_events,
    extract_lab_rows,
    merge_lab_rows,
)
from app.services.hospital_data.source import HospitalDataSource
from app.services.hospital_data.times import TAIPEI

_CATEGORY_ORDER = {category: index for index, category in enumerate(CATEGORY_LABELS)}
# 與 source.py 的檔案快取上限相同：快取的是同一批檔案轉出的內容
_FILE_RECORDS_CACHE_MAX_FILES: Final = 4096


@dataclass(frozen=True)
class TimelineFilter:
    """時間範圍（含起訖日）與類別；`None` 表示不限。"""

    start_date: date | None = None
    end_date: date | None = None
    categories: frozenset[RawRecordCategory] | None = None

    def __post_init__(self) -> None:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise InvalidInputError("起始日期不可晚於結束日期")

    def includes_day(self, day: date) -> bool:
        """這一天是否在範圍內。"""
        is_after_start = self.start_date is None or day >= self.start_date
        return is_after_start and (self.end_date is None or day <= self.end_date)

    def includes_category(self, category: RawRecordCategory) -> bool:
        """這個類別是否要顯示。"""
        return self.categories is None or category in self.categories


def collect_events(source: HospitalDataSource, history: PatientHistory) -> list[TimelineEventRead]:
    """合併所有日期的紀錄並去重，依時間由早到晚排序。"""
    file_records = _read_file_records(source, history)
    section_events = [
        build_identified_event(event_id, content, business_date)
        for event_id, (content, business_date) in _merge_section_contents(file_records).items()
    ]
    lab_events = build_lab_events(_merge_file_lab_rows(file_records))
    return sorted([*section_events, *lab_events], key=_event_sort_key)


def count_events_by_category(
    source: HospitalDataSource, history: PatientHistory
) -> Counter[RawRecordCategory]:
    """各類別的紀錄筆數，與 `collect_events` 的結果一致，但不組出紀錄。"""
    file_records = _read_file_records(source, history)
    counts = Counter(
        content.category for content, _ in _merge_section_contents(file_records).values()
    )
    counts[RawRecordCategory.LAB_RESULT] += count_lab_events(_merge_file_lab_rows(file_records))
    return counts


def collect_lab_rows(source: HospitalDataSource, history: PatientHistory) -> list[LabRow]:
    """合併所有日期的檢驗結果並去重。"""
    return _merge_file_lab_rows(_read_file_records(source, history))


def build_timeline(
    source: HospitalDataSource, history: PatientHistory, timeline_filter: TimelineFilter
) -> PatientTimelineRead:
    """依範圍與類別篩選後，按日分組（日期由新到舊，同日由早到晚）。"""
    events = [
        event
        for event in collect_events(source, history)
        if timeline_filter.includes_category(event.category)
        and timeline_filter.includes_day(event_day(event))
    ]
    days: dict[date, list[TimelineEventRead]] = {}
    for event in events:
        days.setdefault(event_day(event), []).append(event)
    return PatientTimelineRead(
        patient_key=history.patient_key,
        start_date=timeline_filter.start_date,
        end_date=timeline_filter.end_date,
        event_count=len(events),
        days=[TimelineDayRead(day=day, events=days[day]) for day in sorted(days, reverse=True)],
    )


def build_lab_matrix_read(
    source: HospitalDataSource, history: PatientHistory, timeline_filter: TimelineFilter
) -> LabMatrixRead:
    """依時間範圍篩選後的檢驗矩陣。"""
    rows = [
        row
        for row in collect_lab_rows(source, history)
        if timeline_filter.includes_day(_row_day(row))
    ]
    columns, matrix_rows = build_lab_matrix(rows)
    return LabMatrixRead(
        patient_key=history.patient_key,
        start_date=timeline_filter.start_date,
        end_date=timeline_filter.end_date,
        columns=columns,
        rows=matrix_rows,
    )


def iter_patient_files(
    source: HospitalDataSource, history: PatientHistory
) -> Iterator[tuple[date, RawPatientFile]]:
    """依日期由舊到新讀取病人的每個資料檔。"""
    for appearance in history.appearances:
        patient_file = source.read_patient_file(
            appearance.business_date, history.ward_code, appearance.file_name
        )
        yield appearance.business_date, patient_file


def event_day(event: TimelineEventRead) -> date:
    """紀錄歸屬的日期；時間無法解析時以資料日期為準。"""
    if event.occurred_at is None:
        return event.business_date
    return event.occurred_at.astimezone(TAIPEI).date()


@dataclass(frozen=True)
class _FileRecords:
    """一個病人檔轉出的內容；只含不可變物件，多個 thread 共用快取也不會互相影響。"""

    # (event_id, 內容)，順序同 `build_section_contents`
    section_contents: tuple[tuple[str, EventContent], ...]
    lab_rows: tuple[LabRow, ...]


@dataclass(frozen=True, eq=False)
class _SameFile:
    """以「同一個物件」比對病人檔的快取鍵。

    source.py 以「路徑＋修改時間」快取解析結果：檔案未更新時回傳同一個物件，更新後回傳新物件，
    所以以物件身分為鍵即可跟著自動失效。鍵持有物件本身，物件仍在快取中時 `id` 不會被重複使用。
    """

    patient_file: RawPatientFile

    def __hash__(self) -> int:
        return id(self.patient_file)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _SameFile) and other.patient_file is self.patient_file


@lru_cache(maxsize=_FILE_RECORDS_CACHE_MAX_FILES)
def _file_records(file_ref: _SameFile, business_date: date) -> _FileRecords:
    contents = build_section_contents(file_ref.patient_file)
    return _FileRecords(
        section_contents=tuple((content_event_id(content), content) for content in contents),
        lab_rows=tuple(extract_lab_rows(file_ref.patient_file, business_date)),
    )


def _read_file_records(
    source: HospitalDataSource, history: PatientHistory
) -> list[tuple[date, _FileRecords]]:
    # 每個檔案只走訪一次，一般紀錄與檢驗結果都從這裡取
    return [
        (business_date, _file_records(_SameFile(patient_file), business_date))
        for business_date, patient_file in iter_patient_files(source, history)
    ]


def _merge_section_contents(
    file_records: list[tuple[date, _FileRecords]],
) -> dict[str, tuple[EventContent, date]]:
    merged: dict[str, tuple[EventContent, date]] = {}
    # 由舊到新合併，重複的紀錄保留最早出現的資料日期
    for business_date, records in file_records:
        for event_id, content in records.section_contents:
            merged.setdefault(event_id, (content, business_date))
    return merged


def _merge_file_lab_rows(file_records: list[tuple[date, _FileRecords]]) -> list[LabRow]:
    return merge_lab_rows(row for _, records in file_records for row in records.lab_rows)


def _row_day(row: LabRow) -> date:
    if row.time.occurred_at is None:
        return row.business_date
    return row.time.occurred_at.astimezone(TAIPEI).date()


def _event_sort_key(event: TimelineEventRead) -> tuple[date, bool, datetime, int]:
    # 同一天中只有日期的紀錄排在最前面，其餘依時刻、類別排序
    occurred_at = event.occurred_at or datetime.combine(
        event.business_date, datetime.min.time(), TAIPEI
    )
    return (event_day(event), not event.is_date_only, occurred_at, _CATEGORY_ORDER[event.category])
