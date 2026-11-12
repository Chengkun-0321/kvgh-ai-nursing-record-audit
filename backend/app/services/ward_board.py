"""首頁病床總覽：由院方病人清單組出各床狀態，彙總數字與顯示文字在這裡算好。

稽核規則尚未實作，目前每床皆為「尚未稽核」；不捏造判定。
"""

import asyncio
from datetime import date
from typing import Final

from app.core.enums import BedBoardStatus
from app.core.exceptions import NotFoundError
from app.schemas.ward_board import (
    BedStatusRead,
    PatientSummaryRead,
    StatusCountRead,
    WardBedBoardRead,
)
from app.services.hospital_data.events import admitted_at_text
from app.services.hospital_data.index import (
    PatientAppearance,
    list_ward_dates,
    list_ward_histories,
)
from app.services.hospital_data.patients import ward_display_name
from app.services.hospital_data.source import DATE_NOT_FOUND_MESSAGE, HospitalDataSource
from app.services.hospital_data.times import TAIPEI, parse_record_time

# 狀態列的顯示順序與名稱（由嚴重到正常，最後是尚未稽核）
STATUS_LABELS: Final[dict[BedBoardStatus, str]] = {
    BedBoardStatus.ERROR: "缺漏",
    BedBoardStatus.WARNING: "需確認",
    BedBoardStatus.NEEDS_REVIEW: "無法判定",
    BedBoardStatus.PASS: "紀錄完整",
    BedBoardStatus.NOT_AUDITED: "尚未稽核",
}
_EMPTY_FINDINGS_TEXTS: Final[dict[BedBoardStatus, str]] = {
    BedBoardStatus.PASS: "今日稽核項目皆無待確認事項",
    BedBoardStatus.NOT_AUDITED: "此床尚未執行稽核，目前沒有稽核結果",
}
# 待處理病床：已稽核且最嚴重判定不是 PASS
_PENDING_STATUSES: Final = frozenset(
    {BedBoardStatus.ERROR, BedBoardStatus.WARNING, BedBoardStatus.NEEDS_REVIEW}
)


async def get_ward_bed_board(
    source: HospitalDataSource, ward_code: str, business_date: date | None
) -> WardBedBoardRead:
    """取得病床總覽；未指定日期時為該病房最新一天。"""
    return await asyncio.to_thread(build_ward_bed_board, source, ward_code, business_date)


def build_ward_bed_board(
    source: HospitalDataSource, ward_code: str, business_date: date | None
) -> WardBedBoardRead:
    """同步版本，供 thread 執行與測試。"""
    target_date = _resolve_business_date(source, ward_code, business_date)
    beds = [
        _bed_status(source, ward_code, history.patient_key, appearance)
        for history in list_ward_histories(source, ward_code)
        for appearance in history.appearances
        if appearance.business_date == target_date
    ]
    beds.sort(key=lambda bed: bed.bed_code)
    return WardBedBoardRead(
        ward_code=ward_code,
        display_name=ward_display_name(ward_code),
        business_date=target_date,
        bed_count=len(beds),
        pending_bed_count=sum(bed.is_pending for bed in beds),
        status_counts=_status_counts(beds),
        beds=beds,
    )


def _resolve_business_date(
    source: HospitalDataSource, ward_code: str, business_date: date | None
) -> date:
    dates = list_ward_dates(source, ward_code)
    if business_date is None:
        return dates[-1]
    if business_date not in dates:
        raise NotFoundError(DATE_NOT_FOUND_MESSAGE)
    return business_date


def _bed_status(
    source: HospitalDataSource,
    ward_code: str,
    patient_key: str,
    appearance: PatientAppearance,
) -> BedStatusRead:
    business_date = appearance.business_date
    patient_file = source.read_patient_file(business_date, ward_code, appearance.file_name)
    admission_date = _admission_date(admitted_at_text(patient_file))
    status = BedBoardStatus.NOT_AUDITED
    return BedStatusRead(
        bed_code=appearance.bed_code,
        patient=PatientSummaryRead(
            patient_key=patient_key,
            name=None,
            sex=None,
            age_years=None,
            age_group=None,
            admission_date=admission_date,
            length_of_stay_days=_length_of_stay_days(admission_date, business_date),
            diagnosis=None,
        ),
        status=status,
        status_label=STATUS_LABELS[status],
        summary_text=STATUS_LABELS[status],
        is_pending=status in _PENDING_STATUSES,
        pending_findings=[],
        empty_findings_text=_EMPTY_FINDINGS_TEXTS.get(status, ""),
    )


def _admission_date(admitted_at: str | None) -> date | None:
    if admitted_at is None:
        return None
    occurred_at = parse_record_time(admitted_at).occurred_at
    return occurred_at.astimezone(TAIPEI).date() if occurred_at else None


def _length_of_stay_days(admission_date: date | None, business_date: date) -> int | None:
    if admission_date is None:
        return None
    return max(0, (business_date - admission_date).days)


def _status_counts(beds: list[BedStatusRead]) -> list[StatusCountRead]:
    return [
        StatusCountRead(status=status, label=label, count=sum(bed.status == status for bed in beds))
        for status, label in STATUS_LABELS.items()
    ]
