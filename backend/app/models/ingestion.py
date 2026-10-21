"""每日資料包的匯入批次與驗證錯誤。"""

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import IngestionStatus
from app.db.base import Base, CreatedAtMixin, IdMixin

_SOURCE_MAX_LENGTH = 32
_FILE_NAME_MAX_LENGTH = 255
_SHA256_LENGTH = 64
_STATUS_MAX_LENGTH = 32
_JSON_PATH_MAX_LENGTH = 500


class IngestionBatch(IdMixin, CreatedAtMixin, Base):
    """一次資料包匯入；以整包 sha256 判斷是否已匯入過。"""

    __tablename__ = "ingestion_batches"

    source: Mapped[str] = mapped_column(String(_SOURCE_MAX_LENGTH))
    business_date: Mapped[date] = mapped_column(Date, index=True)
    # 例：`20260901/manifest.json`
    file_name: Mapped[str] = mapped_column(String(_FILE_NAME_MAX_LENGTH))
    sha256: Mapped[str] = mapped_column(String(_SHA256_LENGTH), index=True)
    status: Mapped[IngestionStatus] = mapped_column(
        Enum(
            IngestionStatus,
            native_enum=False,
            length=_STATUS_MAX_LENGTH,
            values_callable=lambda members: [member.value for member in members],
        )
    )
    # 以病患檔為單位計
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)


class IngestionError(IdMixin, CreatedAtMixin, Base):
    """單一檔案的驗證錯誤；`message` 只放錯誤類型與說明，不含紀錄內文。"""

    __tablename__ = "ingestion_errors"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("ingestion_batches.id"), index=True
    )
    file_name: Mapped[str] = mapped_column(String(_FILE_NAME_MAX_LENGTH))
    # 例：`$.vital_signs[0].spo2`；整檔錯誤為 `$`
    json_path: Mapped[str] = mapped_column(String(_JSON_PATH_MAX_LENGTH))
    message: Mapped[str] = mapped_column(Text)
