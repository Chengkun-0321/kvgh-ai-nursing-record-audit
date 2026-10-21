"""住院與 R02 相關紀錄的 upsert 與查詢（不 commit，交易邊界在 service）。

upsert 採「先查再新增／更新」，不使用 `ON CONFLICT` 等方言語法，SQLite 與 PostgreSQL 皆可運作。
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base
from app.models.clinical_record import LabResult, NursingProgressNote, Tube, VitalSign


@dataclass(frozen=True)
class RecordScope:
    """查詢範圍：同一病患、同一住院、指定的資料包日期。"""

    patient_key: str
    admission_id: str
    business_dates: Sequence[date]


async def upsert[M: Base](
    session: AsyncSession,
    model: type[M],
    natural_key: Mapping[str, object],
    values: Mapping[str, object],
) -> M:
    """依自然鍵新增；已存在就以新內容覆蓋。

    Args:
        session: DB session。
        model: ORM 類別。
        natural_key: 自然鍵欄位與值，例如 `{"record_id": "NPN-0001"}`。
        values: 其餘欄位的新內容。

    Returns:
        新增或更新後的 ORM 物件（尚未 commit）。
    """
    existing = await session.scalar(select(model).filter_by(**natural_key))
    if existing is None:
        created = model(**natural_key, **values)
        session.add(created)
        await session.flush()
        return created
    for field_name, value in values.items():
        setattr(existing, field_name, value)
    await session.flush()
    return existing


async def list_progress_notes(
    session: AsyncSession, scope: RecordScope
) -> Sequence[NursingProgressNote]:
    """範圍內的護理過程紀錄，依紀錄時間由早到晚。"""
    result = await session.scalars(
        select(NursingProgressNote)
        .where(
            NursingProgressNote.patient_key == scope.patient_key,
            NursingProgressNote.admission_id == scope.admission_id,
            NursingProgressNote.business_date.in_(scope.business_dates),
        )
        .order_by(NursingProgressNote.recorded_at, NursingProgressNote.record_id)
    )
    return result.all()


async def list_vital_signs(session: AsyncSession, scope: RecordScope) -> Sequence[VitalSign]:
    """範圍內的生命徵象，依測量時間由早到晚。"""
    result = await session.scalars(
        select(VitalSign)
        .where(
            VitalSign.patient_key == scope.patient_key,
            VitalSign.admission_id == scope.admission_id,
            VitalSign.business_date.in_(scope.business_dates),
        )
        .order_by(VitalSign.measured_at, VitalSign.record_id)
    )
    return result.all()


async def list_lab_results(session: AsyncSession, scope: RecordScope) -> Sequence[LabResult]:
    """範圍內的檢驗結果，依採檢時間由早到晚。"""
    result = await session.scalars(
        select(LabResult)
        .where(
            LabResult.patient_key == scope.patient_key,
            LabResult.admission_id == scope.admission_id,
            LabResult.business_date.in_(scope.business_dates),
        )
        .order_by(LabResult.collected_at, LabResult.record_id)
    )
    return result.all()


async def list_tubes(session: AsyncSession, scope: RecordScope) -> Sequence[Tube]:
    """範圍內各日的管路現況，依日期與管路 ID 排序。"""
    result = await session.scalars(
        select(Tube)
        .where(
            Tube.patient_key == scope.patient_key,
            Tube.admission_id == scope.admission_id,
            Tube.business_date.in_(scope.business_dates),
        )
        .order_by(Tube.business_date, Tube.tube_id)
    )
    return result.all()
