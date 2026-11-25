"""同一床前後換人：稽核與病床總覽一律以病人（HCASENO）對應資料，不以床號。

情境：W97-021 第 1 天是病人 A，A 出院後第 2 天由病人 B 入住。
B 的稽核資料不得含 A 的任何紀錄，反之亦然；病床總覽每天顯示當天那位病人。
"""

import json
from datetime import date
from pathlib import Path
from typing import Final

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.services.audit.context import AuditContext, build_audit_context
from app.services.hospital_data.source import HospitalDataSource
from app.services.ward_board import BedBoardQuery, get_ward_bed_board

WARD_CODE: Final = "W97"
BED: Final = "021"
BED_CODE: Final = "W97-021"
DAY_1: Final = date(2026, 1, 1)
DAY_2: Final = date(2026, 1, 2)
A_KEY: Final = "3001"
B_KEY: Final = "3002"
A_FILE: Final = "3001_9301.json"
B_FILE: Final = "3002_9302.json"
# 每段紀錄都帶著病人標記，用來檢查有沒有混到另一位病人的內容
A_MARK: Final = "病人A"
B_MARK: Final = "病人B"


def _patient_file(mark: str, admitted: str, day: str) -> dict[str, object]:
    return {
        "病人基本資料": [{"入院時間": admitted, "床號": BED_CODE}],
        "工作清單": [{"基本資料": "有填寫"}],
        "入院經過": [f"{mark}虛構入院經過"],
        "護理記錄": [{"日期": day, "類別": "交班", "內容": f"{mark}虛構交班內容"}],
        "生命徵象": [{"日期": f"{day} 08:00:00", "體溫": "36.5℃", "備註": mark}],
    }


def _patient_list(day: str, key: str, file_name: str) -> dict[str, object]:
    return {
        "資料日期": day,
        "病房": WARD_CODE,
        "病人數": 1,
        "病人名單": [{"床號": BED, "HCASENO": key, "HHISNUM": "0", "檔案": file_name}],
    }


@pytest.fixture
def bed_reuse_source(tmp_path: Path) -> HospitalDataSource:
    """第 1 天 021 床為 A，第 2 天同一床改為 B（A 不在第 2 天名單）。"""
    files = {
        ("20260101", "patientlist.json"): _patient_list("2026-01-01", A_KEY, A_FILE),
        ("20260101", A_FILE): _patient_file(A_MARK, "2025-12-31 10:00:00", "2026-01-01"),
        ("20260102", "patientlist.json"): _patient_list("2026-01-02", B_KEY, B_FILE),
        ("20260102", B_FILE): _patient_file(B_MARK, "2026-01-02 09:00:00", "2026-01-02"),
    }
    root = tmp_path / "bed_reuse"
    for (folder, file_name), content in files.items():
        path = root / folder / WARD_CODE / file_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return HospitalDataSource(root)


def _all_text(ctx: AuditContext) -> str:
    return "\n".join(record.raw_text for record in ctx.records)


async def test_new_patient_in_reused_bed_has_only_own_records(
    bed_reuse_source: HospitalDataSource,
) -> None:
    ctx = await build_audit_context(bed_reuse_source, B_KEY, DAY_2)

    assert ctx.bed_code == BED_CODE
    assert ctx.patient_dates == (DAY_2,)
    assert ctx.admission_date == DAY_2
    assert ctx.records, "B 應有自己的紀錄"
    assert B_MARK in _all_text(ctx)
    assert A_MARK not in _all_text(ctx)
    # 回溯前幾天時也不會讀到 A（B 在第 1 天沒有資料）
    assert ctx.records_on(DAY_1, "nursing_progress_note") == []


async def test_previous_patient_of_bed_has_only_own_records(
    bed_reuse_source: HospitalDataSource,
) -> None:
    ctx = await build_audit_context(bed_reuse_source, A_KEY, DAY_1)

    assert ctx.bed_code == BED_CODE
    assert ctx.patient_dates == (DAY_1,)
    assert A_MARK in _all_text(ctx)
    assert B_MARK not in _all_text(ctx)


async def test_previous_patient_cannot_be_audited_on_day_after_leaving(
    bed_reuse_source: HospitalDataSource,
) -> None:
    # A 已不在第 2 天名單：第 2 天不能用 A 的身分讀到 021 床（B）的資料
    with pytest.raises(NotFoundError):
        await build_audit_context(bed_reuse_source, A_KEY, DAY_2)


@pytest.mark.parametrize(("day", "expected_key"), [(DAY_1, A_KEY), (DAY_2, B_KEY)])
async def test_bed_board_shows_that_days_patient(
    session: AsyncSession,
    bed_reuse_source: HospitalDataSource,
    day: date,
    expected_key: str,
) -> None:
    query = BedBoardQuery(ward_code=WARD_CODE, business_date=day, today=lambda: date(2026, 1, 3))

    board = await get_ward_bed_board(session, bed_reuse_source, query)

    (bed,) = board.beds
    assert (bed.bed_code, bed.patient.patient_key) == (BED_CODE, expected_key)
