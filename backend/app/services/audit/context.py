"""稽核用的病患資料快照：一次備妥某病患所有日期的紀錄，規則只讀取、不再自行讀檔。

資料歸日一律依紀錄本身的時間（`timeline.event_day`），不用資料夾日期：
每日身評、轉床、GCS 是最新快照，同一個檔案可能含有別天的資料（見 docs/conventions/audit-rules.md）。
"""

import asyncio
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Final

from app.core.exceptions import NotFoundError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.services.audit.clock import default_business_date, taipei_today
from app.services.audit.records import SourceRecord, from_timeline_event
from app.services.hospital_data.events import admitted_at_text
from app.services.hospital_data.index import PatientHistory, find_patient_history
from app.services.hospital_data.patients import build_work_checklist
from app.services.hospital_data.source import HospitalDataSource
from app.services.hospital_data.timeline import collect_events
from app.services.hospital_data.times import parse_record_time

DATE_WITHOUT_DATA_MESSAGE: Final = "此病人在該日沒有院方資料"


@dataclass(frozen=True)
class AuditContext:
    """一位病患在某個稽核日的資料快照（不可變）。

    `business_date` 是規則要使用的日期；一次性規則會用 `for_date` 換成入院日後再傳給規則。
    """

    patient_key: str
    ward_code: str
    bed_code: str
    business_date: date
    patient_dates: tuple[date, ...]
    admitted_at: datetime | None
    admitted_at_text: str | None
    work_checklist: WorkChecklistRead
    records: tuple[SourceRecord, ...]

    @property
    def admission_date(self) -> date | None:
        """入院日；院方沒有入院時間時為 `None`。"""
        return self.admitted_at.date() if self.admitted_at else None

    def for_date(self, business_date: date) -> "AuditContext":
        """同一病患、改用另一個稽核日的快照（資料不變）。"""
        return replace(self, business_date=business_date)

    def records_on(self, day: date, source: str | None = None) -> list[SourceRecord]:
        """某日的紀錄；`source` 為 None 時不分類別。"""
        return [record for record in self._of_source(source) if record.business_date == day]

    def records_between(
        self, start: date, end: date, source: str | None = None
    ) -> list[SourceRecord]:
        """起訖日（含）之間的紀錄，例如 R02 往前回溯、R06 往後追蹤。"""
        return [
            record for record in self._of_source(source) if start <= record.business_date <= end
        ]

    def records_of(self, source: str) -> list[SourceRecord]:
        """所有日期中某類別的紀錄，例如入院經過、入院身體評估。"""
        return self._of_source(source)

    def _of_source(self, source: str | None) -> list[SourceRecord]:
        return [record for record in self.records if source is None or record.source == source]


async def build_audit_context(
    source: HospitalDataSource,
    patient_key: str,
    business_date: date | None,
    today: date | None = None,
) -> AuditContext:
    """備妥病患快照；`business_date` 未指定時為已結束的最新一天（見 `clock.py`）。

    `today` 未指定時為台北時間的今天。

    Raises:
        NotFoundError: 查無病人，或該日沒有此病人的資料。
    """
    return await asyncio.to_thread(load_audit_context, source, patient_key, business_date, today)


def load_audit_context(
    source: HospitalDataSource,
    patient_key: str,
    business_date: date | None,
    today: date | None = None,
) -> AuditContext:
    """同步版本的 `build_audit_context`，供已在 thread 中的呼叫端使用。"""
    history = find_patient_history(source, patient_key)
    target = business_date
    if target is None:
        dates = [appearance.business_date for appearance in history.appearances]
        target = default_business_date(dates, today or taipei_today())
    return context_from_history(source, history, target)


def context_from_history(
    source: HospitalDataSource, history: PatientHistory, business_date: date
) -> AuditContext:
    """由病人的出現紀錄組出快照；病患頁與病床總覽共用此函式，確保資料與日期決定方式一致。

    Raises:
        NotFoundError: 該日沒有此病人的資料。
    """
    patient_dates = tuple(appearance.business_date for appearance in history.appearances)
    target = business_date
    if target not in patient_dates:
        raise NotFoundError(DATE_WITHOUT_DATA_MESSAGE)
    latest = history.latest
    latest_file = source.read_patient_file(
        latest.business_date, history.ward_code, latest.file_name
    )
    admitted_text = admitted_at_text(latest_file)
    return AuditContext(
        patient_key=history.patient_key,
        ward_code=history.ward_code,
        bed_code=history.appearance_on(target).bed_code,
        business_date=target,
        patient_dates=patient_dates,
        admitted_at=parse_record_time(admitted_text).occurred_at if admitted_text else None,
        admitted_at_text=admitted_text,
        work_checklist=build_work_checklist(latest_file),
        records=tuple(from_timeline_event(event) for event in collect_events(source, history)),
    )
