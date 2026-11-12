"""由各日期的 patientlist.json 整理出「哪位病人、哪天、在哪一床、檔名為何」。"""

from dataclasses import dataclass
from datetime import date
from typing import Final

from app.core.exceptions import NotFoundError
from app.schemas.hospital_data.raw import RawPatientListEntry
from app.services.hospital_data.source import WARD_NOT_FOUND_MESSAGE, HospitalDataSource

PATIENT_NOT_FOUND_MESSAGE: Final = "查無此病人的院方資料"
_BED_CODE_SEPARATOR: Final = "-"


@dataclass(frozen=True)
class PatientAppearance:
    """病人出現在某日病人清單的一次紀錄。"""

    business_date: date
    bed_code: str
    file_name: str


@dataclass(frozen=True)
class PatientHistory:
    """一位病人在某病房所有日期的出現紀錄（由舊到新）。"""

    patient_key: str
    ward_code: str
    appearances: tuple[PatientAppearance, ...]

    @property
    def latest(self) -> PatientAppearance:
        """最新一天的紀錄。"""
        return self.appearances[-1]

    def appearance_on(self, business_date: date) -> PatientAppearance:
        """指定日期的紀錄；該日沒有這位病人時拋出 `NotFoundError`。"""
        for appearance in self.appearances:
            if appearance.business_date == business_date:
                return appearance
        raise NotFoundError(PATIENT_NOT_FOUND_MESSAGE)


def normalize_bed_code(raw_bed_code: str, ward_code: str) -> str:
    """統一床號為「病房-床位」：patientlist 只寫床位（`001`），病人檔寫 `W63-001`。

    不是本病房格式的床號（含其他病房代碼或非數字）照原樣回傳，不猜測。
    """
    stripped = raw_bed_code.strip()
    bed_number = stripped.removeprefix(ward_code).lstrip(_BED_CODE_SEPARATOR)
    if not bed_number.isdigit():
        return stripped
    return f"{ward_code}{_BED_CODE_SEPARATOR}{bed_number}"


def scan_ward_dates(source: HospitalDataSource) -> dict[str, list[date]]:
    """掃描一次資料目錄：各病房有病人清單的日期（由舊到新），病房依代碼排序。

    同一個請求需要多個病房或多次查日期時，先呼叫本函式再傳下去，避免重複掃描目錄。
    """
    ward_dates: dict[str, list[date]] = {}
    for business_date in source.list_business_dates():
        for ward_code in source.list_ward_codes(business_date):
            ward_dates.setdefault(ward_code, []).append(business_date)
    return dict(sorted(ward_dates.items()))


def list_ward_dates(source: HospitalDataSource, ward_code: str) -> list[date]:
    """該病房有病人清單的日期（由舊到新）；完全沒有時拋出 `NotFoundError`。"""
    dates = scan_ward_dates(source).get(ward_code)
    if not dates:
        raise NotFoundError(WARD_NOT_FOUND_MESSAGE)
    return dates


def list_day_appearances(
    source: HospitalDataSource, ward_code: str, business_date: date
) -> list[tuple[str, PatientAppearance]]:
    """某日病人清單中的每位病人（依院方清單順序），以 `(patient_key, 出現紀錄)` 表示。"""
    return [
        (entry.patient_key, _appearance(entry, business_date, ward_code))
        for entry in source.read_patient_list(business_date, ward_code).patients
    ]


def list_ward_histories(
    source: HospitalDataSource, ward_code: str, ward_dates: list[date]
) -> list[PatientHistory]:
    """該病房 `ward_dates`（由舊到新，取自 `list_ward_dates`）出現過的病人，依最新床號排序。"""
    appearances: dict[str, list[PatientAppearance]] = {}
    for business_date in ward_dates:
        for patient_key, appearance in list_day_appearances(source, ward_code, business_date):
            appearances.setdefault(patient_key, []).append(appearance)
    histories = [
        PatientHistory(patient_key=key, ward_code=ward_code, appearances=tuple(items))
        for key, items in appearances.items()
    ]
    return sorted(histories, key=lambda history: history.latest.bed_code)


def find_patient_history(source: HospitalDataSource, patient_key: str) -> PatientHistory:
    """在所有病房中（依代碼順序）找出這位病人第一個出現的病房；找不到時拋出 `NotFoundError`。"""
    for ward_code, ward_dates in scan_ward_dates(source).items():
        appearances = _appearances_of(source, ward_code, ward_dates, patient_key)
        if appearances:
            return PatientHistory(
                patient_key=patient_key, ward_code=ward_code, appearances=appearances
            )
    raise NotFoundError(PATIENT_NOT_FOUND_MESSAGE)


def _appearances_of(
    source: HospitalDataSource, ward_code: str, ward_dates: list[date], patient_key: str
) -> tuple[PatientAppearance, ...]:
    # 只為目標病人建立出現紀錄，不必先組出整個病房的歷史再比對
    return tuple(
        _appearance(entry, business_date, ward_code)
        for business_date in ward_dates
        for entry in source.read_patient_list(business_date, ward_code).patients
        if entry.patient_key == patient_key
    )


def _appearance(
    entry: RawPatientListEntry, business_date: date, ward_code: str
) -> PatientAppearance:
    return PatientAppearance(
        business_date=business_date,
        bed_code=normalize_bed_code(entry.bed_code, ward_code),
        file_name=entry.file_name,
    )
