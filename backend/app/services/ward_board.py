"""首頁病床總覽：由院方病人清單與最新稽核結果組出各床狀態，彙總數字在這裡算好。

院方檔讀取（同步 I/O）在 thread 中完成；稽核結果以一次批次查詢取回。床位狀態的計算見
`ward_board_status.py`（純函式）。稽核日與可否稽核與病患頁共用 `services/audit/service.py`。
"""

import asyncio
from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.crud import audit_run as audit_run_crud
from app.models.audit import AuditRun
from app.schemas.ward_board import (
    BedStatusRead,
    PatientSummaryRead,
    StatusCountRead,
    WardBedBoardRead,
)
from app.services.audit.clock import TodayProvider, default_business_date
from app.services.audit.context import context_from_history
from app.services.audit.registry import RULE_REGISTRY
from app.services.audit.service import effective_business_date
from app.services.hospital_data.events import admitted_at_text
from app.services.hospital_data.index import PatientHistory, list_ward_dates, list_ward_histories
from app.services.hospital_data.patients import ward_display_name
from app.services.hospital_data.source import DATE_NOT_FOUND_MESSAGE, HospitalDataSource
from app.services.hospital_data.times import TAIPEI, parse_record_time
from app.services.ward_board_status import (
    STATUS_LABELS,
    BedSnapshot,
    RunKey,
    build_bed_status,
    run_key,
)


@dataclass(frozen=True)
class BedBoardQuery:
    """病床總覽的查詢：病房、稽核日（未指定為預設日）、「今天」的來源。"""

    ward_code: str
    business_date: date | None
    today: TodayProvider


async def get_ward_bed_board(
    session: AsyncSession,
    source: HospitalDataSource,
    query: BedBoardQuery,
) -> WardBedBoardRead:
    """取得病床總覽；未指定日期時為已結束的最新一天（沒有時為最新一天）。

    「今天」只在此取用一次，整份總覽用同一個值，與病患頁的判斷一致。
    """
    today_date = query.today()
    snapshot = await asyncio.to_thread(
        load_ward_day, source, query.ward_code, query.business_date, today_date
    )
    latest = await _latest_runs(session, snapshot.beds)
    beds = sorted(
        (build_bed_status(bed, latest, today_date) for bed in snapshot.beds),
        key=lambda bed: bed.bed_code,
    )
    ward_code = query.ward_code
    return WardBedBoardRead(
        ward_code=ward_code,
        display_name=ward_display_name(ward_code),
        business_date=snapshot.business_date,
        bed_count=len(beds),
        pending_bed_count=sum(bed.is_pending for bed in beds),
        status_counts=_status_counts(beds),
        beds=beds,
    )


@dataclass(frozen=True)
class WardDaySnapshot:
    """某病房某日的病床快照（`load_ward_day` 的回傳結構）。"""

    business_date: date
    beds: list[BedSnapshot]


def load_ward_day(
    source: HospitalDataSource, ward_code: str, business_date: date | None, today: date
) -> WardDaySnapshot:
    """同步讀取某病房某日的所有病床（供 thread 執行）。

    病患的資料快照與病患頁共用 `context_from_history`；同一病人在病患頁與病床總覽的紀錄與日期一致。
    """
    ward_dates = list_ward_dates(source, ward_code)
    target = _resolve_business_date(ward_dates, business_date, today)
    histories = list_ward_histories(source, ward_code, ward_dates)
    beds = [
        _bed_snapshot(source, ward_code, history, target)
        for history in histories
        if history.appears_on(target)
    ]
    return WardDaySnapshot(business_date=target, beds=beds)


def _resolve_business_date(dates: list[date], business_date: date | None, today: date) -> date:
    """與病患頁相同的預設規則（見 `clock.default_business_date`）。"""
    if business_date is None:
        return default_business_date(dates, today)
    if business_date not in dates:
        raise NotFoundError(DATE_NOT_FOUND_MESSAGE)
    return business_date


def _bed_snapshot(
    source: HospitalDataSource, ward_code: str, history: PatientHistory, target: date
) -> BedSnapshot:
    ctx = context_from_history(source, history, target)  # 目標日已由呼叫端確認存在
    appearance = history.appearance_on(target)
    # 入院日取自該日的病人檔（與原本病床總覽相同），而非最新一天的檔案
    patient_file = source.read_patient_file(target, ward_code, appearance.file_name)
    admission_date = _admission_date(admitted_at_text(patient_file))
    patient = PatientSummaryRead(
        patient_key=history.patient_key,
        name=None,
        sex=None,
        age_years=None,
        age_group=None,
        admission_date=admission_date,
        length_of_stay_days=_length_of_stay_days(admission_date, target),
    )
    return BedSnapshot(bed_code=appearance.bed_code, patient=patient, ctx=ctx)


async def _latest_runs(session: AsyncSession, beds: list[BedSnapshot]) -> dict[RunKey, AuditRun]:
    """所有病床、所有規則在其稽核日的最新執行，一次查詢取回。"""
    if not beds:
        return {}
    runs = await audit_run_crud.list_latest_runs(
        session,
        patient_keys=[bed.patient_key for bed in beds],
        rule_codes=list(RULE_REGISTRY),
        business_dates=_candidate_days(beds),
    )
    return {run_key(run): run for run in runs}


def _candidate_days(beds: list[BedSnapshot]) -> list[date]:
    """規則可能使用的稽核日（入院規則為入院日，其餘為所選日期）。"""
    return sorted(
        {effective_business_date(rule, bed.ctx) for bed in beds for rule in RULE_REGISTRY.values()}
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
