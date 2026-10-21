"""list_audit_days 測試：BR1（日期清單與可否稽核）、E10（manifest 缺失）、E1。"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from r02_support import FakeStructuredLLM, prompt_dates, render, run_r02
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PatientNotFoundError
from app.services.audit.runner import list_audit_days
from app.services.ingestion.sources import LocalFixtureSource

FIRST_DAY_REASON = "入院首日，無前日紀錄可比較"


async def _days(session: AsyncSession, root: Path, patient_key: str) -> list[dict[str, Any]]:
    result = await list_audit_days(
        session=session, source=LocalFixtureSource(root), patient_key=patient_key
    )
    dumped: dict[str, Any] = result.model_dump(mode="json")
    assert dumped["patient_key"] == patient_key
    days: list[dict[str, Any]] = dumped["days"]
    return days


async def _days_by_date(
    session: AsyncSession, root: Path, patient_key: str
) -> dict[str, dict[str, Any]]:
    days = await _days(session, root, patient_key)
    return {day["business_date"]: day for day in days}


async def test_br1_p001_days_are_listed_newest_first(
    session: AsyncSession, data_root: Path
) -> None:
    """BR1：P001 出現在 9/01、9/02、9/03、9/05 的 manifest，由新到舊列出。"""
    days = await _days(session, data_root, "P001")

    assert [day["business_date"] for day in days] == [
        "2026-09-05",
        "2026-09-03",
        "2026-09-02",
        "2026-09-01",
    ]


async def test_br1_p001_first_day_not_auditable_others_auditable(
    session: AsyncSession, data_root: Path
) -> None:
    """BR1 邊界：9/01 為入院首日不可稽核；9/05 前一天缺資料包仍可稽核。

    不可稽核的原因為「入院首日，無前日紀錄可比較」（有逗號），
    可稽核者原因為 None。
    """
    days = await _days_by_date(session, data_root, "P001")

    assert days["2026-09-01"]["auditable"] is False
    assert days["2026-09-01"]["not_auditable_reason"] == FIRST_DAY_REASON
    for key in ("2026-09-02", "2026-09-03", "2026-09-05"):
        assert days[key]["auditable"] is True
        assert days[key]["not_auditable_reason"] is None


async def test_br1_p002_readmission_first_day_not_auditable(
    session: AsyncSession, data_root: Path
) -> None:
    """BR1 邊界：P002 9/03 換成新的 admission_id（再次住院首日）。

    9/01 不可、9/02 可、9/03 不可；admission_id 欄位值正確。
    """
    days = await _days_by_date(session, data_root, "P002")

    assert list(days) == ["2026-09-03", "2026-09-02", "2026-09-01"]
    assert days["2026-09-01"]["auditable"] is False
    assert days["2026-09-02"]["auditable"] is True
    assert days["2026-09-03"]["auditable"] is False
    assert days["2026-09-03"]["not_auditable_reason"] == FIRST_DAY_REASON
    assert days["2026-09-01"]["admission_id"] == "ADM-P002-01"
    assert days["2026-09-02"]["admission_id"] == "ADM-P002-01"
    assert days["2026-09-03"]["admission_id"] == "ADM-P002-02"


async def test_br1_latest_finding_is_none_before_any_audit(
    session: AsyncSession, data_root: Path
) -> None:
    """BR1：尚未稽核時每一天的 latest_finding 都是 None。

    P001 各日的 admission_id 都是 ADM-P001-01。
    """
    days = await _days(session, data_root, "P001")

    assert all(day["latest_finding"] is None for day in days)
    assert all(day["admission_id"] == "ADM-P001-01" for day in days)


async def test_e1_unknown_patient_raises_not_found(session: AsyncSession, data_root: Path) -> None:
    """E1：patient_key 沒有出現在任何 manifest → PatientNotFoundError。"""
    source = LocalFixtureSource(data_root)

    with pytest.raises(PatientNotFoundError):
        await list_audit_days(session=session, source=source, patient_key="NOPE")


def _break_manifests(root: Path) -> None:
    """E10 變形：刪除 9/03 的 manifest；新增 9/06 資料夾放無法解析的 manifest。"""
    (root / "20260903" / "manifest.json").unlink()
    (root / "20260906").mkdir()
    (root / "20260906" / "manifest.json").write_text("{bad json", encoding="utf-8")


async def test_e10_missing_or_broken_manifest_days_are_hidden(
    session: AsyncSession, data_root: Path
) -> None:
    """E10：manifest 不存在（9/03）或無法解析（9/06）的日期不出現。"""
    _break_manifests(data_root)

    p001 = [day["business_date"] for day in await _days(session, data_root, "P001")]
    p002 = [day["business_date"] for day in await _days(session, data_root, "P002")]

    assert p001 == ["2026-09-05", "2026-09-02", "2026-09-01"]
    assert p002 == ["2026-09-02", "2026-09-01"]


async def test_e10_missing_manifest_day_excluded_from_comparison_scope(
    session: AsyncSession, data_root: Path
) -> None:
    """E10：9/03 的 manifest 不存在 → 不納入比對範圍。

    稽核 P001 9/05 的比對範圍改為 9/05、9/02、9/01。
    """
    _break_manifests(data_root)
    llm = FakeStructuredLLM()

    await run_r02(session, data_root, llm, patient_key="P001", business_date=date(2026, 9, 5))

    assert llm.calls == 1
    prompt = render(llm.requests[0])
    assert prompt_dates(prompt) == {"2026-09-05", "2026-09-02", "2026-09-01"}
    assert "NPN-P001-0903-01" not in prompt
