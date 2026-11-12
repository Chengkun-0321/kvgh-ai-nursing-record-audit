"""院方資料來源：路徑驗證與檔案讀取。"""

from datetime import date
from pathlib import Path

import pytest

from app.core.exceptions import HospitalDataError, NotFoundError
from app.services.hospital_data.index import normalize_bed_code
from app.services.hospital_data.source import HospitalDataSource
from tests.hospital_data_samples import P1_FILE, WARD_CODE

DAY_1 = date(2026, 1, 1)


def test_lists_dates_and_wards(hospital_data_source: HospitalDataSource) -> None:
    assert hospital_data_source.list_business_dates() == [DAY_1, date(2026, 1, 2)]
    assert hospital_data_source.list_ward_codes(DAY_1) == [WARD_CODE]


def test_invalid_date_folder_is_skipped(
    hospital_data_source: HospitalDataSource, tmp_path: Path
) -> None:
    (tmp_path / "hospital_data" / "20261399").mkdir()
    assert hospital_data_source.list_business_dates() == [DAY_1, date(2026, 1, 2)]


def test_missing_root_has_no_dates(tmp_path: Path) -> None:
    assert HospitalDataSource(tmp_path / "missing").list_business_dates() == []


@pytest.mark.parametrize("ward_code", ["../W99", "W99/..", "w99", ""])
def test_rejects_invalid_ward_code(
    hospital_data_source: HospitalDataSource, ward_code: str
) -> None:
    with pytest.raises(NotFoundError):
        hospital_data_source.read_patient_list(DAY_1, ward_code)


@pytest.mark.parametrize("file_name", ["../patientlist.json", "a/b.json", "x.txt", "missing.json"])
def test_rejects_invalid_patient_file(
    hospital_data_source: HospitalDataSource, file_name: str
) -> None:
    with pytest.raises(HospitalDataError):
        hospital_data_source.read_patient_file(DAY_1, WARD_CODE, file_name)


def test_broken_json_raises_hospital_data_error(
    hospital_data_source: HospitalDataSource, tmp_path: Path
) -> None:
    broken = tmp_path / "hospital_data" / "20260101" / WARD_CODE / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(HospitalDataError):
        hospital_data_source.read_patient_file(DAY_1, WARD_CODE, "broken.json")


def test_symlinked_ward_outside_root_is_rejected(
    hospital_data_source: HospitalDataSource, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "patientlist.json").write_text("{}", encoding="utf-8")
    (tmp_path / "hospital_data" / "20260101" / "W98").symlink_to(outside)
    with pytest.raises(NotFoundError):
        hospital_data_source.read_patient_list(DAY_1, "W98")


def test_reads_patient_file_sections(hospital_data_source: HospitalDataSource) -> None:
    patient_file = hospital_data_source.read_patient_file(DAY_1, WARD_CODE, P1_FILE)
    assert len(patient_file.records("檢驗報告")) == 3
    assert patient_file.texts("入院經過") == ["虛構入院經過"]
    assert patient_file.records("不存在的區塊") == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("001", "W63-001"), ("W63-001", "W63-001"), ("W63001", "W63-001"), ("W51-001", "W51-001")],
)
def test_normalize_bed_code(raw: str, expected: str) -> None:
    assert normalize_bed_code(raw, "W63") == expected
