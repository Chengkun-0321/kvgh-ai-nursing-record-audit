"""病患快照：資料依紀錄本身的時間歸日，不依資料夾日期。"""

from datetime import date

import pytest

from app.core.exceptions import NotFoundError
from app.services.audit.context import build_audit_context
from app.services.hospital_data.source import HospitalDataSource
from tests.hospital_data_samples import AUDIT_P3_KEY

ASSESSMENT = "daily_physical_assessment"


async def test_snapshot_assessment_is_dated_by_its_own_time(
    audit_hospital_data_source: HospitalDataSource,
) -> None:
    ctx = await build_audit_context(audit_hospital_data_source, AUDIT_P3_KEY, None)

    # 第一天的檔案就帶著 2026-01-02 的身評，只能歸到 01-02，且兩個檔案的重複紀錄只留一筆
    assessments = ctx.records_of(ASSESSMENT)
    assert [record.business_date for record in assessments] == [date(2026, 1, 2)]
    assert ctx.records_on(date(2026, 1, 1), ASSESSMENT) == []


async def test_default_date_is_latest_patient_date_and_admission_is_parsed(
    audit_hospital_data_source: HospitalDataSource,
) -> None:
    ctx = await build_audit_context(audit_hospital_data_source, AUDIT_P3_KEY, None)

    assert ctx.business_date == date(2026, 1, 2)
    assert ctx.patient_dates == (date(2026, 1, 1), date(2026, 1, 2))
    assert ctx.bed_code == "W98-001"
    assert ctx.admission_date == date(2025, 12, 31)


async def test_records_between_is_inclusive_and_filters_by_source(
    audit_hospital_data_source: HospitalDataSource,
) -> None:
    ctx = await build_audit_context(audit_hospital_data_source, AUDIT_P3_KEY, date(2026, 1, 2))

    notes = ctx.records_between(date(2026, 1, 1), date(2026, 1, 2), "nursing_progress_note")

    assert sorted(record.business_date for record in notes) == [date(2026, 1, 1), date(2026, 1, 2)]
    assert ctx.records_on(date(2026, 1, 2), "consultation") == []


async def test_admission_course_and_checklist_are_available(
    audit_hospital_data_source: HospitalDataSource,
) -> None:
    ctx = await build_audit_context(audit_hospital_data_source, AUDIT_P3_KEY, None)

    assert len(ctx.records_of("admission_course")) == 1
    assert ctx.work_checklist.total_count == 7
    assert [item.label for item in ctx.work_checklist.items if not item.is_filled] == ["個人病史"]


async def test_for_date_changes_only_the_business_date(
    audit_hospital_data_source: HospitalDataSource,
) -> None:
    ctx = await build_audit_context(audit_hospital_data_source, AUDIT_P3_KEY, None)

    moved = ctx.for_date(date(2025, 12, 31))

    assert moved.business_date == date(2025, 12, 31)
    assert moved.records == ctx.records


async def test_date_without_patient_data_is_not_found(
    audit_hospital_data_source: HospitalDataSource,
) -> None:
    with pytest.raises(NotFoundError):
        await build_audit_context(audit_hospital_data_source, AUDIT_P3_KEY, date(2026, 3, 1))


async def test_unknown_patient_is_not_found(audit_hospital_data_source: HospitalDataSource) -> None:
    with pytest.raises(NotFoundError):
        await build_audit_context(audit_hospital_data_source, "9999", None)
