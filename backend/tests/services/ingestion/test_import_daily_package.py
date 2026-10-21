"""import_daily_package 測試。

- BR4：匯入步驟、重複匯入、以新內容覆蓋
- B3：原始檔原封複製、來源只讀
- E9：病患檔驗證失敗
"""

import uuid
from datetime import date
from pathlib import Path
from typing import Any

from r02_support import (
    ALL_TABLES,
    RECORD_TABLES,
    count_all,
    count_rows,
    edit_json,
    file_sha256,
    patient_file,
    read_json,
    snapshot,
    table_cells,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ingestion.importer import import_daily_package
from app.services.ingestion.sources import LocalFixtureSource

SEP_02 = date(2026, 9, 2)
UNIQUE_CONTENT = "虛構獨特內文XYZ"
NEW_CONTENT = "虛構更新後內文，病人今日改為自行下床活動。"


def _expected_record_counts(root: Path, day: str) -> dict[str, int]:
    """依資料包內容計算各資料表應有的筆數。"""
    files = [read_json(path) for path in sorted((root / day).glob("P*.json"))]
    admission_ids = {data["patient"]["admission_id"] for data in files}
    tube_ids = {tube["tube_id"] for data in files for tube in data["tubes"]}
    return {
        "admissions": len(admission_ids),
        "nursing_progress_notes": sum(len(data["nursing_progress_notes"]) for data in files),
        "vital_signs": sum(len(data["vital_signs"]) for data in files),
        "lab_results": sum(len(data["lab_results"]) for data in files),
        "tubes": len(tube_ids),
    }


async def test_br4_import_copies_raw_files_and_writes_one_batch(
    session: AsyncSession, data_root: Path, tmp_path: Path
) -> None:
    """BR4：匯入 9/02 → 原始檔複製到 RAW_DATA_DIR/2026-09-02/。

    ingestion_batches 恰好 1 筆，sha256 非空、business_date 正確。
    """
    source = LocalFixtureSource(data_root)

    summary = await import_daily_package(session, source, SEP_02)

    raw_dir = tmp_path / "raw" / "2026-09-02"
    assert (raw_dir / "manifest.json").is_file()
    assert (raw_dir / "P001.json").is_file()
    assert (raw_dir / "P002.json").is_file()
    query = text("SELECT business_date, sha256 FROM ingestion_batches")
    rows = (await session.execute(query)).all()
    assert len(rows) == 1
    assert str(rows[0][0]).startswith("2026-09-02")
    assert rows[0][1]
    assert summary.skipped is False


async def test_br4_import_normalizes_r02_records(session: AsyncSession, data_root: Path) -> None:
    """BR4：病患／住院、護理過程紀錄、生命徵象、檢驗、管路依資料包內容入庫。"""
    source = LocalFixtureSource(data_root)
    expected = _expected_record_counts(data_root, "20260902")

    await import_daily_package(session, source, SEP_02)

    assert await count_all(session, RECORD_TABLES) == expected


async def test_br4_reimport_same_package_adds_nothing(
    session: AsyncSession, data_root: Path
) -> None:
    """BR4 邊界：同一份資料包匯入兩次 → 重複 0 筆新增。

    所有資料表筆數不變，第二次 summary.skipped 為 True。
    """
    source = LocalFixtureSource(data_root)
    await import_daily_package(session, source, SEP_02)
    before = await count_all(session, ALL_TABLES)

    second = await import_daily_package(session, source, SEP_02)

    assert await count_all(session, ALL_TABLES) == before
    assert second.skipped is True


async def test_br4_changed_content_overwrites_existing_record(
    session: AsyncSession, data_root: Path
) -> None:
    """BR4：內容改變後再匯入 → 同一 record_id 只有 1 筆，內容為新內容。"""
    source = LocalFixtureSource(data_root)
    await import_daily_package(session, source, SEP_02)
    notes_before = await count_rows(session, "nursing_progress_notes")
    p001_path = patient_file(data_root, "20260902", "P001")
    old_content = read_json(p001_path)["nursing_progress_notes"][0]["content"]

    def _update(data: dict[str, Any]) -> None:
        data["nursing_progress_notes"][0]["content"] = NEW_CONTENT

    edit_json(p001_path, _update)

    await import_daily_package(session, source, SEP_02)

    assert await count_rows(session, "nursing_progress_notes") == notes_before
    cells = await table_cells(session, "nursing_progress_notes")
    assert NEW_CONTENT in cells
    assert old_content not in cells
    assert cells.count("NPN-P001-0902-01") == 1


async def test_b3_import_keeps_source_untouched_and_raw_copy_identical(
    session: AsyncSession, data_root: Path, tmp_path: Path
) -> None:
    """B3：匯入前後 MOCK_DATA_DIR 快照相同。

    RAW_DATA_DIR/2026-09-02/ 下各原始檔的 sha256 與來源檔相同。
    """
    before = snapshot(data_root)
    source = LocalFixtureSource(data_root)

    await import_daily_package(session, source, SEP_02)

    assert snapshot(data_root) == before
    raw_dir = tmp_path / "raw" / "2026-09-02"
    for name in ("manifest.json", "P001.json", "P002.json"):
        source_file = data_root / "20260902" / name
        assert file_sha256(raw_dir / name) == file_sha256(source_file)


async def test_e9_invalid_patient_file_records_error_without_content(
    session: AsyncSession, data_root: Path
) -> None:
    """E9：P001 9/02 的 spo2 改成 "abc"，並在內文放入獨特字串。

    - ingestion_errors 有該批次的紀錄：檔名 P001.json、JSON path 含 vital_signs
    - 錯誤訊息不含紀錄內文、不含原值 abc
    - 同批的 P002 照常匯入
    """

    def _break(data: dict[str, Any]) -> None:
        data["vital_signs"][0]["spo2"] = "abc"
        data["nursing_progress_notes"][0]["content"] = UNIQUE_CONTENT

    edit_json(patient_file(data_root, "20260902", "P001"), _break)
    source = LocalFixtureSource(data_root)

    summary = await import_daily_package(session, source, SEP_02)

    query = text("SELECT batch_id, file_name, json_path, message FROM ingestion_errors")
    rows = (await session.execute(query)).all()
    matching = [row for row in rows if row[1] == "P001.json"]
    assert matching, "應有 P001.json 的驗證錯誤紀錄"
    assert any("vital_signs" in str(row[2]) for row in matching)
    for row in rows:
        assert uuid.UUID(str(row[0])) == uuid.UUID(str(summary.batch_id))
        assert UNIQUE_CONTENT not in str(row[3])
        assert "abc" not in str(row[3])
    cells = await table_cells(session, "nursing_progress_notes")
    assert "NPN-P002-0902-01" in cells
