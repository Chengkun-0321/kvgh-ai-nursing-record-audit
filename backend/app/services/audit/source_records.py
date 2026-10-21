"""把 `AuditContext` 中的資料轉成送給 LLM 的原文 `text`（固定格式），供規則共用。

Evidence 的原文片段也以同一段 `text` 驗證；格式屬於 prompt 的一部分，
改變格式時應同時提升 prompt 版本，已保存的稽核結果才能重現。
"""

from datetime import datetime
from typing import Final

from app.core.constants import BUSINESS_TIMEZONE
from app.core.enums import RecordSource
from app.services.audit.base import (
    AuditContext,
    LabResultRecord,
    ProgressNoteRecord,
    SourceRecord,
    TubeRecord,
    VitalSignRecord,
)

_MISSING: Final = "未記錄"
_SEPARATOR: Final = "｜"
_DATETIME_FORMAT: Final = "%Y-%m-%d %H:%M"


def build_source_records(ctx: AuditContext) -> list[SourceRecord]:
    """依資料類型組出每筆資料的原文：護理過程紀錄在前，其後為生命徵象、檢驗、管路。"""
    return [
        *(_from_progress_note(note) for note in ctx.progress_notes),
        *(_from_vital_sign(vital) for vital in ctx.vital_signs),
        *(_from_lab_result(lab) for lab in ctx.lab_results),
        *(_from_tube(tube) for tube in ctx.tubes),
    ]


def format_local_datetime(value: datetime) -> str:
    """以 Asia/Taipei 顯示時間，例：`2026-09-04 14:00`。"""
    return value.astimezone(BUSINESS_TIMEZONE).strftime(_DATETIME_FORMAT)


def _value(value: object, unit: str = "") -> str:
    return _MISSING if value is None else f"{value}{unit}"


def _from_progress_note(note: ProgressNoteRecord) -> SourceRecord:
    recorded_at = format_local_datetime(note.recorded_at)
    return SourceRecord(
        source=RecordSource.NURSING_PROGRESS_NOTE,
        record_id=note.record_id,
        business_date=note.business_date,
        recorded_at=note.recorded_at,
        text=f"{note.title}\n{note.content}",
        note=_SEPARATOR.join((f"紀錄時間 {recorded_at}", f"標籤 {note.title_category}")),
    )


def _from_vital_sign(vital: VitalSignRecord) -> SourceRecord:
    site = f"（{vital.temperature_site}）" if vital.temperature_site else ""
    parts = (
        f"測量時間 {format_local_datetime(vital.measured_at)}",
        f"體溫 {_value(vital.body_temperature, '℃')}{site}",
        f"脈搏 {_value(vital.pulse, ' 次/分')}",
        f"呼吸 {_value(vital.respiration, ' 次/分')}",
        f"血壓 {_value(vital.sbp)}/{_value(vital.dbp)} mmHg",
        f"SpO2 {_value(vital.spo2, '%')}",
        f"給氧 {_value(vital.oxygen_therapy)}",
    )
    return SourceRecord(
        source=RecordSource.VITAL_SIGN,
        record_id=vital.record_id,
        business_date=vital.business_date,
        recorded_at=vital.measured_at,
        text=_SEPARATOR.join(parts),
    )


def _from_lab_result(lab: LabResultRecord) -> SourceRecord:
    unit = f" {lab.unit}" if lab.unit else ""
    parts = (
        f"採檢時間 {format_local_datetime(lab.collected_at)}",
        lab.order_name,
        f"{lab.item} {lab.value}{unit}",
        f"參考值 {_value(lab.reference_range)}",
        f"註記 {lab.abnormal_flag or '無'}",
    )
    return SourceRecord(
        source=RecordSource.LAB_RESULT,
        record_id=lab.record_id,
        business_date=lab.business_date,
        recorded_at=lab.collected_at,
        text=_SEPARATOR.join(parts),
    )


def _from_tube(tube: TubeRecord) -> SourceRecord:
    parts = (
        tube.tube_type,
        f"部位 {tube.site}",
        f"尺寸 {_value(tube.size)}",
        f"置放日 {tube.inserted_on.isoformat() if tube.inserted_on else '不詳'}",
        f"移除日 {tube.removed_on.isoformat() if tube.removed_on else '未移除'}",
        f"固定 {_value(tube.fixation)}",
        f"外觀 {_value(tube.appearance)}",
    )
    return SourceRecord(
        source=RecordSource.TUBE,
        record_id=tube.tube_id,
        business_date=tube.business_date,
        recorded_at=None,
        text=_SEPARATOR.join(parts),
    )
