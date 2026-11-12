"""院方每日資料來源：讀取 `<root>/<YYYYMMDD>/<病房>/` 底下的檔案，只讀不寫。

整個 `app/` 只有本模組會開啟院方資料目錄的檔案。日期、病房、檔名都先比對格式，
再確認解析後的路徑仍在資料目錄內，防止路徑穿越。
"""

import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from app.core.constants import WARD_CODE_PATTERN
from app.core.exceptions import HospitalDataError, NotFoundError
from app.schemas.hospital_data.raw import RawPatientFile, RawPatientList

PATIENT_LIST_FILE_NAME: Final = "patientlist.json"
_FOLDER_DATE_FORMAT: Final = "%Y%m%d"
_DATE_FOLDER_PATTERN: Final = re.compile(r"^\d{8}$")
_WARD_CODE_PATTERN: Final = re.compile(WARD_CODE_PATTERN)
_PATIENT_FILE_PATTERN: Final = re.compile(r"^[0-9A-Za-z_-]{1,64}\.json$")
# 院方資料量小（每日每病房數十個檔），快取足以涵蓋數十天
_CACHE_MAX_FILES: Final = 4096

WARD_NOT_FOUND_MESSAGE: Final = "查無此病房的院方資料"
DATE_NOT_FOUND_MESSAGE: Final = "查無此日期的院方資料"
_UNREADABLE_MESSAGE: Final = "院方資料檔無法讀取或格式不符，請確認資料來源"


class HospitalDataSource:
    """讀取本機院方資料目錄；未來改接中繼站時實作相同的公開方法即可。"""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def list_business_dates(self) -> list[date]:
        """列出有資料的日期（由舊到新）；資料目錄不存在時為空。"""
        if not self._root.is_dir():
            return []
        names = [p.name for p in self._root.iterdir() if p.is_dir()]
        dates = (_parse_folder_date(name) for name in names)
        return sorted(d for d in dates if d is not None)

    def list_ward_codes(self, business_date: date) -> list[str]:
        """列出該日有 patientlist.json 的病房代碼。"""
        date_dir = self._root / _folder_name(business_date)
        if not date_dir.is_dir():
            return []
        return sorted(
            p.name
            for p in date_dir.iterdir()
            if _WARD_CODE_PATTERN.match(p.name) and (p / PATIENT_LIST_FILE_NAME).is_file()
        )

    def read_patient_list(self, business_date: date, ward_code: str) -> RawPatientList:
        """讀取該日該病房的 patientlist.json。"""
        path = (self._ward_dir(business_date, ward_code) / PATIENT_LIST_FILE_NAME).resolve()
        # 合法名稱的目錄仍可能是指向外部的符號連結，解析後須仍在資料目錄內
        if not path.is_relative_to(self._root) or not path.is_file():
            raise NotFoundError(DATE_NOT_FOUND_MESSAGE)
        return _load_patient_list(str(path), _mtime_ns(path))

    def read_patient_file(
        self, business_date: date, ward_code: str, file_name: str
    ) -> RawPatientFile:
        """讀取該日該病房的一個病人檔。"""
        path = self._patient_path(business_date, ward_code, file_name)
        return _load_patient_file(str(path), _mtime_ns(path))

    def read_patient_text(self, business_date: date, ward_code: str, file_name: str) -> str:
        """讀取病人檔原文（供畫面「看原文」核對）。"""
        path = self._patient_path(business_date, ward_code, file_name)
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise HospitalDataError(_UNREADABLE_MESSAGE) from error

    def _ward_dir(self, business_date: date, ward_code: str) -> Path:
        if not _WARD_CODE_PATTERN.match(ward_code):
            raise NotFoundError(WARD_NOT_FOUND_MESSAGE)
        return self._root / _folder_name(business_date) / ward_code

    def _patient_path(self, business_date: date, ward_code: str, file_name: str) -> Path:
        if not _PATIENT_FILE_PATTERN.match(file_name):
            raise HospitalDataError(_UNREADABLE_MESSAGE)
        path = (self._ward_dir(business_date, ward_code) / file_name).resolve()
        if not path.is_relative_to(self._root) or not path.is_file():
            raise HospitalDataError(_UNREADABLE_MESSAGE)
        return path


def _mtime_ns(path: Path) -> int:
    # 檔案在檢查後被移除等 I/O 錯誤轉成 AppError，避免例外訊息帶出含識別碼的檔案路徑
    try:
        return path.stat().st_mtime_ns
    except OSError as error:
        raise HospitalDataError(_UNREADABLE_MESSAGE) from error


def _folder_name(business_date: date) -> str:
    return business_date.strftime(_FOLDER_DATE_FORMAT)


def _parse_folder_date(name: str) -> date | None:
    # ISO 8601 基本格式（YYYYMMDD）；八位數但不是合法日期（如 20261399）的資料夾略過
    if not _DATE_FOLDER_PATTERN.match(name):
        return None
    try:
        return date.fromisoformat(name)
    except ValueError:
        return None


# 以「路徑＋修改時間」為快取鍵：院方更新檔案後自動重新讀取，未更新時不重複解析
@lru_cache(maxsize=_CACHE_MAX_FILES)
def _load_patient_list(path: str, _mtime_ns: int) -> RawPatientList:
    try:
        return RawPatientList.model_validate(_read_json(path))
    except ValidationError as error:
        raise HospitalDataError(_UNREADABLE_MESSAGE) from error


@lru_cache(maxsize=_CACHE_MAX_FILES)
def _load_patient_file(path: str, _mtime_ns: int) -> RawPatientFile:
    try:
        return RawPatientFile.model_validate(_read_json(path))
    except ValidationError as error:
        raise HospitalDataError(_UNREADABLE_MESSAGE) from error


def _read_json(path: str) -> object:
    try:
        with Path(path).open(encoding="utf-8") as file:
            return json.load(file)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HospitalDataError(_UNREADABLE_MESSAGE) from error
