"""合併一位病人各日期的資料檔，組出時間軸與檢驗矩陣（同步函式，由 service 放到 thread 執行）。

院方每天的檔案只含當天紀錄，但「檢查」會帶歷史紀錄，所以合併時以內容去重。
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime

from app.core.enums import RawRecordCategory
from app.core.exceptions import InvalidInputError
from app.schemas.hospital_data.raw import RawPatientFile
from app.schemas.hospital_data.timeline import (
    LabMatrixRead,
    PatientTimelineRead,
    TimelineDayRead,
    TimelineEventRead,
)
from app.services.hospital_data.events import CATEGORY_LABELS, build_section_events
from app.services.hospital_data.index import PatientHistory
from app.services.hospital_data.labs import (
    LabRow,
    build_lab_events,
    build_lab_matrix,
    extract_lab_rows,
    merge_lab_rows,
)
from app.services.hospital_data.source import HospitalDataSource
from app.services.hospital_data.times import TAIPEI

_CATEGORY_ORDER = {category: index for index, category in enumerate(CATEGORY_LABELS)}


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
    merged: dict[str, TimelineEventRead] = {}
    # 由舊到新讀取，重複的紀錄保留最早出現的資料日期
    for business_date, patient_file in iter_patient_files(source, history):
        for event in build_section_events(patient_file, business_date):
            merged.setdefault(event.event_id, event)
    lab_events = build_lab_events(collect_lab_rows(source, history))
    events = [*merged.values(), *lab_events]
    return sorted(events, key=_event_sort_key)


def collect_lab_rows(source: HospitalDataSource, history: PatientHistory) -> list[LabRow]:
    """合併所有日期的檢驗結果並去重。"""
    rows = [
        row
        for business_date, patient_file in iter_patient_files(source, history)
        for row in extract_lab_rows(patient_file, business_date)
    ]
    return merge_lab_rows(rows)


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
