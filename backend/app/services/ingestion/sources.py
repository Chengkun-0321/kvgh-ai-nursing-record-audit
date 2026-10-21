"""資料來源：讀取院方每日資料包的原始檔（只讀，不寫入、不修改來源）。

`LocalFixtureSource` 讀取 `<root>/<YYYYMMDD>/`；未來的中繼站來源實作同一個 `DataSource` 介面，
匯入流程不需修改。整個 `app/` 只有本模組會開啟資料目錄底下的檔案。
"""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final, Protocol

from pydantic import ValidationError

from app.schemas.ingestion import Manifest

logger = logging.getLogger(__name__)

MANIFEST_FILE_NAME: Final = "manifest.json"
REJECTED_OUTSIDE_ROOT: Final = "檔案路徑不在資料目錄內"
REJECTED_NOT_FOUND: Final = "找不到檔案"
REJECTED_UNREADABLE: Final = "無法讀取檔案"
FOLDER_DATE_FORMAT: Final = "%Y%m%d"
_FOLDER_NAME_PATTERN: Final = re.compile(r"^\d{8}$")


@dataclass(frozen=True)
class RawDocument:
    """資料包中的一個原始檔；無法讀取或被拒絕時 `content` 為 `None` 並附原因。"""

    business_date: date
    # 相對於日期資料夾，例：`manifest.json`、`A病患.json`
    file_name: str
    content: bytes | None
    rejected_reason: str | None = None

    @property
    def sha256(self) -> str | None:
        """原始內容的 sha256（hex）；沒有內容時為 `None`。"""
        if self.content is None:
            return None
        return hashlib.sha256(self.content).hexdigest()


class DataSource(Protocol):
    """每日資料包來源。"""

    source_name: str

    def list_business_dates(self) -> list[date]:
        """列出有資料包的業務日期（由舊到新）。"""

    async def fetch_manifest(self, business_date: date) -> RawDocument:
        """取得該日的 `manifest.json`。"""

    async def fetch(self, business_date: date) -> list[RawDocument]:
        """取得該日的 manifest 與清單內所有病患檔（manifest 在第一個）。"""


def parse_manifest(document: RawDocument) -> Manifest | None:
    """依 v0.1.0 驗證 manifest；不存在、無法解析或不符格式時回傳 `None`（E10）。"""
    if document.content is None:
        return None
    try:
        return Manifest.model_validate_json(document.content)
    except ValidationError:
        return None


def folder_name(business_date: date) -> str:
    """業務日期對應的資料夾名稱（YYYYMMDD）。"""
    return business_date.strftime(FOLDER_DATE_FORMAT)


class LocalFixtureSource:
    """讀取本機目錄（目前為 `mock_data/`）的每日資料包。"""

    source_name: str = "local"

    def __init__(self, root: Path) -> None:
        """建立來源；不在建構時讀取目錄。

        Args:
            root: 資料包根目錄，底下為 `<YYYYMMDD>/` 資料夾。
        """
        self._root = root

    def list_business_dates(self) -> list[date]:
        """列出名稱為 8 位數字且為合法日期的資料夾（由舊到新）；其他資料夾忽略（E11）。"""
        if not self._root.is_dir():
            return []
        dates = (_parse_folder_date(path) for path in self._root.iterdir())
        return sorted(business_date for business_date in dates if business_date is not None)

    async def fetch_manifest(self, business_date: date) -> RawDocument:
        """讀取該日的 `manifest.json`；不存在時回傳沒有內容的 `RawDocument`。"""
        path = self._root / folder_name(business_date) / MANIFEST_FILE_NAME
        return await asyncio.to_thread(_read_document, business_date, MANIFEST_FILE_NAME, path)

    async def fetch(self, business_date: date) -> list[RawDocument]:
        """讀取 manifest 與清單內的病患檔；manifest 不符格式時只回傳 manifest。"""
        manifest_document = await self.fetch_manifest(business_date)
        manifest = parse_manifest(manifest_document)
        if manifest is None:
            return [manifest_document]
        patient_documents = [
            await self._fetch_patient_file(business_date, entry.file) for entry in manifest.patients
        ]
        return [manifest_document, *patient_documents]

    async def _fetch_patient_file(self, business_date: date, file_name: str) -> RawDocument:
        path = self._resolve_inside_root(business_date, file_name)
        if path is None:
            # 只記日期，不記檔名（檔名含院方病患代碼）
            logger.warning("拒絕讀取資料目錄外的檔案：business_date=%s", business_date)
            return RawDocument(business_date, file_name, None, REJECTED_OUTSIDE_ROOT)
        return await asyncio.to_thread(_read_document, business_date, file_name, path)

    def _resolve_inside_root(self, business_date: date, file_name: str) -> Path | None:
        """manifest 的 `file` 解析後必須仍在資料目錄內，防止 path traversal（E11）。"""
        if Path(file_name).is_absolute():
            return None
        resolved = (self._root / folder_name(business_date) / file_name).resolve()
        if not resolved.is_relative_to(self._root.resolve()):
            return None
        return resolved


def _parse_folder_date(path: Path) -> date | None:
    name = path.name
    if not _FOLDER_NAME_PATTERN.match(name) or not path.is_dir():
        return None
    try:
        return date(int(name[:4]), int(name[4:6]), int(name[6:]))
    except ValueError:
        return None


def _read_document(business_date: date, file_name: str, path: Path) -> RawDocument:
    if not path.is_file():
        return RawDocument(business_date, file_name, None, REJECTED_NOT_FOUND)
    try:
        content = path.read_bytes()
    except OSError:
        return RawDocument(business_date, file_name, None, REJECTED_UNREADABLE)
    return RawDocument(business_date, file_name, content)
