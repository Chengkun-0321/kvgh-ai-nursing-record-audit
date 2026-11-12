"""由各日期的 patientlist.json 整理出「哪位病人、哪天、在哪一床、檔名為何」。"""

from dataclasses import dataclass
from datetime import date
from typing import Final

from app.core.exceptions import NotFoundError
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


def list_ward_dates(source: HospitalDataSource, ward_code: str) -> list[date]:
    """該病房有病人清單的日期（由舊到新）；完全沒有時拋出 `NotFoundError`。"""
    dates = [d for d in source.list_business_dates() if ward_code in source.list_ward_codes(d)]
    if not dates:
        raise NotFoundError(WARD_NOT_FOUND_MESSAGE)
    return dates


def list_ward_histories(source: HospitalDataSource, ward_code: str) -> list[PatientHistory]:
    """該病房所有日期出現過的病人，依最新床號排序。"""
    appearances: dict[str, list[PatientAppearance]] = {}
    for business_date in list_ward_dates(source, ward_code):
        for entry in source.read_patient_list(business_date, ward_code).patients:
            appearances.setdefault(entry.patient_key, []).append(
                PatientAppearance(
                    business_date=business_date,
                    bed_code=normalize_bed_code(entry.bed_code, ward_code),
                    file_name=entry.file_name,
                )
            )
    histories = [
        PatientHistory(patient_key=key, ward_code=ward_code, appearances=tuple(items))
        for key, items in appearances.items()
    ]
    return sorted(histories, key=lambda history: history.latest.bed_code)


def find_patient_history(source: HospitalDataSource, patient_key: str) -> PatientHistory:
    """在所有病房中找出這位病人；找不到時拋出 `NotFoundError`。"""
    for ward_code in list_all_ward_codes(source):
        for history in list_ward_histories(source, ward_code):
            if history.patient_key == patient_key:
                return history
    raise NotFoundError(PATIENT_NOT_FOUND_MESSAGE)


def list_all_ward_codes(source: HospitalDataSource) -> list[str]:
    """所有日期出現過的病房代碼。"""
    codes = {code for d in source.list_business_dates() for code in source.list_ward_codes(d)}
    return sorted(codes)
