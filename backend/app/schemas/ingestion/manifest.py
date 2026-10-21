"""資料包清單 `manifest.json`（對照 manifest.schema.json）。"""

from datetime import date
from typing import Annotated

from pydantic import AwareDatetime, Field

from app.schemas.ingestion.common import (
    IngestionModel,
    NonEmptyStr,
    PatientStatus,
    SchemaVersion,
)

_JSON_FILE_PATTERN = r"\.json$"


class ManifestPatient(IngestionModel):
    """清單中的一位病患與其檔案。"""

    patient_id: NonEmptyStr
    file: Annotated[str, Field(pattern=_JSON_FILE_PATTERN)]
    bed_code: NonEmptyStr
    status: PatientStatus


class Manifest(IngestionModel):
    """一個業務日的資料包清單。"""

    schema_version: SchemaVersion
    ward_code: NonEmptyStr
    ward_name: NonEmptyStr
    business_date: date
    generated_at: AwareDatetime
    patient_count: Annotated[int, Field(ge=0)]
    patients: list[ManifestPatient]

    def find_patient(self, patient_id: str) -> ManifestPatient | None:
        """依院方病患代碼找出清單項目；不在清單內時回傳 `None`。"""
        return next((entry for entry in self.patients if entry.patient_id == patient_id), None)
