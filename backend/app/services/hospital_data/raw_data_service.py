"""原始資料頁的 service：endpoint 只呼叫本模組。

讀檔與合併是同步的檔案 I/O，一律放到 thread 執行，避免阻塞 event loop。
"""

import asyncio
from datetime import date

from app.schemas.hospital_data.patients import (
    RawPatientDetailRead,
    RawPatientListRead,
    RawSourceRead,
    WardListRead,
)
from app.schemas.hospital_data.timeline import LabMatrixRead, PatientTimelineRead
from app.services.hospital_data import patients, timeline
from app.services.hospital_data.index import find_patient_history
from app.services.hospital_data.source import HospitalDataSource
from app.services.hospital_data.timeline import TimelineFilter


async def list_wards(source: HospitalDataSource, default_ward_code: str) -> WardListRead:
    """所有有院方資料的病房。"""
    return await asyncio.to_thread(patients.list_wards, source, default_ward_code)


async def list_raw_patients(source: HospitalDataSource, ward_code: str) -> RawPatientListRead:
    """某病房所有日期出現過的病人。"""
    return await asyncio.to_thread(patients.list_raw_patients, source, ward_code)


async def get_patient_detail(source: HospitalDataSource, patient_key: str) -> RawPatientDetailRead:
    """病人摘要。"""
    return await asyncio.to_thread(_patient_detail, source, patient_key)


async def get_patient_timeline(
    source: HospitalDataSource, patient_key: str, timeline_filter: TimelineFilter
) -> PatientTimelineRead:
    """病人時間軸。"""
    return await asyncio.to_thread(_patient_timeline, source, patient_key, timeline_filter)


async def get_lab_matrix(
    source: HospitalDataSource, patient_key: str, timeline_filter: TimelineFilter
) -> LabMatrixRead:
    """病人檢驗矩陣。"""
    return await asyncio.to_thread(_lab_matrix, source, patient_key, timeline_filter)


async def get_patient_source(
    source: HospitalDataSource, patient_key: str, business_date: date | None
) -> RawSourceRead:
    """病人某日資料檔的原文。"""
    return await asyncio.to_thread(_patient_source, source, patient_key, business_date)


def _patient_detail(source: HospitalDataSource, patient_key: str) -> RawPatientDetailRead:
    return patients.build_patient_detail(source, find_patient_history(source, patient_key))


def _patient_timeline(
    source: HospitalDataSource, patient_key: str, timeline_filter: TimelineFilter
) -> PatientTimelineRead:
    history = find_patient_history(source, patient_key)
    return timeline.build_timeline(source, history, timeline_filter)


def _lab_matrix(
    source: HospitalDataSource, patient_key: str, timeline_filter: TimelineFilter
) -> LabMatrixRead:
    history = find_patient_history(source, patient_key)
    return timeline.build_lab_matrix_read(source, history, timeline_filter)


def _patient_source(
    source: HospitalDataSource, patient_key: str, business_date: date | None
) -> RawSourceRead:
    history = find_patient_history(source, patient_key)
    return patients.read_patient_source(source, history, business_date)
