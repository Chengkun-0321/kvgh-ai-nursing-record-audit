"""病房 API：病房清單、首頁病床總覽、原始資料頁的病人清單。"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path

from app.api.deps import HospitalData
from app.core.config import get_settings
from app.core.constants import WARD_CODE_PATTERN
from app.schemas.hospital_data.patients import RawPatientListRead, WardListRead
from app.schemas.ward_board import WardBedBoardRead
from app.services import ward_board
from app.services.hospital_data import raw_data_service

router = APIRouter(prefix="/wards", tags=["病房"])

WardCode = Annotated[str, Path(pattern=WARD_CODE_PATTERN, description="病房代碼，例：W63")]


@router.get("", response_model=WardListRead, summary="列出有院方資料的病房")
async def list_wards(source: HospitalData) -> WardListRead:
    return await raw_data_service.list_wards(source, get_settings().DEFAULT_WARD_CODE)


@router.get("/{ward_code}/bed-board", response_model=WardBedBoardRead, summary="取得病房的病床總覽")
async def get_bed_board(
    ward_code: WardCode, source: HospitalData, business_date: date | None = None
) -> WardBedBoardRead:
    return await ward_board.get_ward_bed_board(source, ward_code, business_date)


@router.get(
    "/{ward_code}/raw-patients",
    response_model=RawPatientListRead,
    summary="列出病房所有日期出現過的病人（原始資料頁）",
)
async def list_raw_patients(ward_code: WardCode, source: HospitalData) -> RawPatientListRead:
    return await raw_data_service.list_raw_patients(source, ward_code)
