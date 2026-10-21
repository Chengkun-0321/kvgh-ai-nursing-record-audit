"""匯入每日資料包：保存原始檔 → 寫入批次 → 驗證 → 正規化 → 入庫。

只依賴 `DataSource` 介面，不知道資料實際放在哪裡。只 `flush`、不 `commit`，交易由呼叫端控制。
"""

import asyncio
import hashlib
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Final

from pydantic import ValidationError
from pydantic_core import ErrorDetails
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import IngestionStatus
from app.crud import clinical_record as clinical_record_crud
from app.crud import ingestion as ingestion_crud
from app.models.ingestion import IngestionBatch, IngestionError
from app.schemas.ingestion import PatientDaily
from app.services.ingestion.normalizers import normalize_patient_daily
from app.services.ingestion.sources import (
    MANIFEST_FILE_NAME,
    DataSource,
    RawDocument,
    folder_name,
    parse_manifest,
)

logger = logging.getLogger(__name__)

WHOLE_FILE_JSON_PATH: Final = "$"
_INVALID_MANIFEST_MESSAGE: Final = "資料包清單不存在或不符格式"
_FILE_SEPARATOR: Final = b"\0"


@dataclass(frozen=True)
class IngestionSummary:
    """一次匯入的摘要；`skipped=True` 表示同一份資料包已匯入過。"""

    batch_id: uuid.UUID | None
    skipped: bool
    success_count: int
    failed_count: int
    skipped_count: int


async def import_daily_package(
    session: AsyncSession, source: DataSource, business_date: date
) -> IngestionSummary:
    """匯入一個業務日的資料包；同一份內容（sha256 相同）不重複匯入。

    Args:
        session: DB session（只 flush，不 commit）。
        source: 資料來源。
        business_date: 業務日期。

    Returns:
        匯入摘要；筆數以病患檔為單位。
    """
    documents = await source.fetch(business_date)
    package_sha256 = compute_package_sha256(documents)
    patient_documents = [doc for doc in documents if doc.file_name != MANIFEST_FILE_NAME]
    existing = await ingestion_crud.get_batch_by_sha256(session, package_sha256)
    if existing is not None:
        logger.info("資料包已匯入過，略過：batch_id=%s", existing.id)
        return IngestionSummary(
            batch_id=existing.id,
            skipped=True,
            success_count=0,
            failed_count=0,
            skipped_count=len(patient_documents),
        )

    raw_root = get_settings().RAW_DATA_DIR
    await asyncio.to_thread(_save_raw_documents, raw_root, documents)
    batch = await ingestion_crud.add_batch(
        session,
        IngestionBatch(
            source=source.source_name,
            business_date=business_date,
            file_name=f"{folder_name(business_date)}/{MANIFEST_FILE_NAME}",
            sha256=package_sha256,
            status=IngestionStatus.FAILED,
        ),
    )
    if not await _check_manifest(session, batch.id, documents):
        return await _finish_batch(session, batch, IngestionStatus.FAILED, (0, 0))

    success_count = 0
    for document in patient_documents:
        success_count += await _import_patient_document(session, batch.id, document)
    failed_count = len(patient_documents) - success_count
    status = _batch_status(success_count, failed_count)
    return await _finish_batch(session, batch, status, (success_count, failed_count))


def compute_package_sha256(documents: Sequence[RawDocument]) -> str:
    """整包資料的 sha256：依序餵入檔名、分隔字元與內容（被拒的檔案只有檔名）。"""
    digest = hashlib.sha256()
    for document in documents:
        digest.update(document.file_name.encode("utf-8"))
        digest.update(_FILE_SEPARATOR)
        if document.content is not None:
            digest.update(document.content)
    return digest.hexdigest()


def to_json_path(location: Sequence[int | str]) -> str:
    """把 Pydantic 錯誤位置轉成 JSON path，例：`$.vital_signs[0].spo2`。"""
    path = WHOLE_FILE_JSON_PATH
    for part in location:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


async def _check_manifest(
    session: AsyncSession, batch_id: uuid.UUID, documents: Sequence[RawDocument]
) -> bool:
    manifest = next((doc for doc in documents if doc.file_name == MANIFEST_FILE_NAME), None)
    if manifest is not None and parse_manifest(manifest) is not None:
        return True
    logger.warning("資料包清單不符格式：batch_id=%s", batch_id)
    error = IngestionError(
        batch_id=batch_id,
        file_name=MANIFEST_FILE_NAME,
        json_path=WHOLE_FILE_JSON_PATH,
        message=_INVALID_MANIFEST_MESSAGE,
    )
    await ingestion_crud.add_errors(session, [error])
    return False


async def _import_patient_document(
    session: AsyncSession, batch_id: uuid.UUID, document: RawDocument
) -> int:
    """驗證並入庫一個病患檔；成功回傳 1，失敗寫入 `ingestion_errors` 並回傳 0。"""
    if document.content is None:
        reason = document.rejected_reason or "無法讀取檔案"
        await ingestion_crud.add_errors(
            session, [_build_error(batch_id, document.file_name, WHOLE_FILE_JSON_PATH, reason)]
        )
        logger.warning("病患檔無法讀取：batch_id=%s", batch_id)
        return 0
    try:
        daily = PatientDaily.model_validate_json(document.content)
    except ValidationError as exc:
        await ingestion_crud.add_errors(
            session, _validation_errors(batch_id, document.file_name, exc)
        )
        logger.warning("病患檔驗證失敗：batch_id=%s errors=%d", batch_id, exc.error_count())
        return 0
    for model, rows in normalize_patient_daily(daily, document.business_date):
        for row in rows:
            await clinical_record_crud.upsert(session, model, row.natural_key, row.values)
    return 1


def _validation_errors(
    batch_id: uuid.UUID, file_name: str, exc: ValidationError
) -> list[IngestionError]:
    # 只保留錯誤類型與說明；不放 input、ctx，避免把紀錄內文寫進 DB
    return [
        _build_error(batch_id, file_name, to_json_path(error["loc"]), _describe(error))
        for error in exc.errors(include_url=False, include_context=False, include_input=False)
    ]


def _describe(error: ErrorDetails) -> str:
    return f"{error['type']}: {error['msg']}"


def _build_error(
    batch_id: uuid.UUID, file_name: str, json_path: str, message: str
) -> IngestionError:
    return IngestionError(
        batch_id=batch_id, file_name=file_name, json_path=json_path, message=message
    )


async def _finish_batch(
    session: AsyncSession,
    batch: IngestionBatch,
    status: IngestionStatus,
    counts: tuple[int, int],
) -> IngestionSummary:
    success_count, failed_count = counts
    batch.success_count = success_count
    batch.failed_count = failed_count
    batch.skipped_count = 0
    batch.status = status
    await session.flush()
    logger.info(
        "資料包匯入完成：batch_id=%s status=%s success=%d failed=%d",
        batch.id,
        batch.status,
        success_count,
        failed_count,
    )
    return IngestionSummary(
        batch_id=batch.id,
        skipped=False,
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=0,
    )


def _batch_status(success_count: int, failed_count: int) -> IngestionStatus:
    if failed_count == 0:
        return IngestionStatus.COMPLETED
    if success_count == 0:
        return IngestionStatus.FAILED
    return IngestionStatus.COMPLETED_WITH_ERRORS


def _save_raw_documents(raw_root: Path, documents: Sequence[RawDocument]) -> None:
    """原始檔原封保存到 `<RAW_DATA_DIR>/<YYYY-MM-DD>/<檔名>`；被拒或無法讀取的檔案不保存。"""
    for document in documents:
        if document.content is None:
            continue
        day_dir = (raw_root / document.business_date.isoformat()).resolve()
        target = (day_dir / document.file_name).resolve()
        if not target.is_relative_to(day_dir):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(document.content)
