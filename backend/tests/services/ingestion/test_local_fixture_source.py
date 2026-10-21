"""LocalFixtureSource 測試：B3（只讀）、E11（資料夾名稱、越界路徑）。"""

from datetime import date
from pathlib import Path
from typing import Any

from r02_support import edit_json, read_json, snapshot, write_json

from app.services.ingestion.sources import LocalFixtureSource

OUTSIDE_MARKER = "虛構外部檔案標記QQQ"


def _set_first_patient_file(root: Path, day: str, file_value: str) -> None:
    def _editor(manifest: dict[str, Any]) -> None:
        manifest["patients"][0]["file"] = file_value

    edit_json(root / day / "manifest.json", _editor)


def test_e11_list_business_dates_ignores_invalid_folder_names(data_root: Path) -> None:
    """E11：名稱不是 8 位數字的資料夾、同名的檔案都被忽略。

    結果由舊到新；9/04 沒有資料夾，不出現。
    """
    for name in ("abc", "2026090", "2026-09-04", "202609011"):
        (data_root / name).mkdir()
    (data_root / "20260907").write_text("不是資料夾", encoding="utf-8")
    source = LocalFixtureSource(data_root)

    dates = source.list_business_dates()

    assert dates == [
        date(2026, 9, 1),
        date(2026, 9, 2),
        date(2026, 9, 3),
        date(2026, 9, 5),
    ]


async def test_e11_manifest_file_outside_root_is_rejected(data_root: Path, tmp_path: Path) -> None:
    """E11：manifest 的 file 為 ../../outside.json（離開 MOCK_DATA_DIR）。

    預期不讀取該檔：該項 content 為 None、有拒絕原因，任何項目都不含外部檔內容。
    """
    outside_data = read_json(data_root / "20260903" / "P001.json")
    outside_data["nursing_progress_notes"][0]["content"] = OUTSIDE_MARKER
    write_json(tmp_path / "outside.json", outside_data)
    _set_first_patient_file(data_root, "20260903", "../../outside.json")
    source = LocalFixtureSource(data_root)

    documents = await source.fetch(date(2026, 9, 3))

    assert any(doc.content is None for doc in documents)
    for doc in documents:
        assert doc.content is None or OUTSIDE_MARKER.encode() not in doc.content
    rejected = [doc for doc in documents if doc.content is None]
    assert all(doc.rejected_reason for doc in rejected)


async def test_e11_parent_path_still_inside_root_is_allowed(data_root: Path) -> None:
    """E11 邊界：../20260902/P001.json 解析後仍在 MOCK_DATA_DIR 內。

    不算越界，可讀到該檔內容。
    """
    _set_first_patient_file(data_root, "20260903", "../20260902/P001.json")
    source = LocalFixtureSource(data_root)

    documents = await source.fetch(date(2026, 9, 3))

    expected = (data_root / "20260902" / "P001.json").read_bytes()
    assert any(doc.content == expected for doc in documents)


async def test_b3_fetch_does_not_modify_mock_data_dir(data_root: Path) -> None:
    """B3：LocalFixtureSource 只讀，讀取前後目錄快照相同。

    快照包含每個檔案的相對路徑、sha256、st_mtime_ns 與目錄清單。
    """
    before = snapshot(data_root)
    source = LocalFixtureSource(data_root)

    source.list_business_dates()
    await source.fetch_manifest(date(2026, 9, 2))
    documents = await source.fetch(date(2026, 9, 2))

    assert snapshot(data_root) == before
    manifest_bytes = (data_root / "20260902" / "manifest.json").read_bytes()
    assert any(doc.content == manifest_bytes for doc in documents)
    assert all(doc.business_date == date(2026, 9, 2) for doc in documents)
