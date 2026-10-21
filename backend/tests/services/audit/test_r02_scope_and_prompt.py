"""R02 比對範圍與 prompt 測試：BR2、BR3（先匯入、不重複匯入）、BR5、A12。"""

from datetime import date
from pathlib import Path

import pytest
from r02_support import (
    RECORD_TABLES,
    FakeStructuredLLM,
    batch_dates,
    count_all,
    count_rows,
    day_blocks,
    patient_file,
    prompt_dates,
    read_json,
    record_ids,
    record_tags,
    render,
    run_r02,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.audit.rules.r02_copy_paste import (
    R02_REQUIRED_ELEMENTS,
    R02LLMOutput,
)
from app.services.ingestion.importer import import_daily_package
from app.services.ingestion.sources import LocalFixtureSource
from app.services.llm.prompt_loader import prompt_id

ALL_DAYS = (date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 5))
SEP_03 = date(2026, 9, 3)


async def _import_until(session: AsyncSession, root: Path, last_day: date) -> None:
    """先匯入 last_day 以前（含）的所有資料包。

    讓比對範圍只由規則決定，而不是由「匯入了哪些日期」決定。
    """
    source = LocalFixtureSource(root)
    for day in ALL_DAYS:
        if day <= last_day:
            await import_daily_package(session, source, day)


async def _prompt_for(
    session: AsyncSession, root: Path, patient_key: str, business_date: date
) -> str:
    llm = FakeStructuredLLM()
    await run_r02(session, root, llm, patient_key=patient_key, business_date=business_date)
    assert llm.calls == 1
    return render(llm.requests[0])


def _p001_contents(root: Path, day: str) -> list[str]:
    notes = read_json(patient_file(root, day, "P001"))["nursing_progress_notes"]
    return [str(item["content"]) for item in notes]


@pytest.mark.parametrize(
    ("patient_key", "business_date", "expected_dates"),
    [
        pytest.param(
            "P001",
            date(2026, 9, 5),
            {"2026-09-05", "2026-09-03", "2026-09-02"},
            id="BR2-skip-missing-0904-exactly-2-days",
        ),
        pytest.param(
            "P001",
            date(2026, 9, 2),
            {"2026-09-02", "2026-09-01"},
            id="BR2-only-1-previous-day",
        ),
        pytest.param(
            "P001",
            date(2026, 9, 3),
            {"2026-09-03", "2026-09-02", "2026-09-01"},
            id="BR2-exactly-2-previous-days",
        ),
        pytest.param(
            "P002",
            date(2026, 9, 2),
            {"2026-09-02", "2026-09-01"},
            id="BR2-p002-own-records-only",
        ),
    ],
)
async def test_br2_comparison_scope_dates(
    *,
    session: AsyncSession,
    data_root: Path,
    patient_key: str,
    business_date: date,
    expected_dates: set[str],
) -> None:
    """BR2：比對範圍＝當日＋同住院中早於當日、有資料包的最近 2 個業務日。

    以渲染後 prompt 中出現的 date="..." 集合檢查；
    缺日跳過，不含其他病患的紀錄。
    """
    await _import_until(session, data_root, business_date)

    prompt = await _prompt_for(session, data_root, patient_key, business_date)

    assert prompt_dates(prompt) == expected_dates
    ids = record_ids(prompt)
    assert ids, "prompt 中應有 record 標籤"
    assert all(patient_key in record_id for record_id in ids)


async def test_br3_audit_imports_each_date_in_scope(session: AsyncSession, data_root: Path) -> None:
    """BR3：稽核 P001 9/03 後，範圍內 9/01～9/03 各有匯入批次，9/05 沒有。"""
    llm = FakeStructuredLLM()

    await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    expected = {"2026-09-01", "2026-09-02", "2026-09-03"}
    assert set(await batch_dates(session)) == expected


async def test_br3_out_of_scope_dates_not_imported(session: AsyncSession, data_root: Path) -> None:
    """BR3：稽核 P001 9/02 後不應有 9/03、9/05 的批次。"""
    llm = FakeStructuredLLM()

    await run_r02(session, data_root, llm, patient_key="P001", business_date=date(2026, 9, 2))

    assert set(await batch_dates(session)) == {"2026-09-01", "2026-09-02"}


async def test_br3_second_audit_does_not_reimport(session: AsyncSession, data_root: Path) -> None:
    """BR3：對同一天再稽核一次，ingestion_batches 與各紀錄表筆數不變。"""
    await run_r02(session, data_root, FakeStructuredLLM(), patient_key="P001", business_date=SEP_03)
    batches_before = await count_rows(session, "ingestion_batches")
    records_before = await count_all(session, RECORD_TABLES)

    await run_r02(session, data_root, FakeStructuredLLM(), patient_key="P001", business_date=SEP_03)

    assert await count_rows(session, "ingestion_batches") == batches_before
    assert await count_all(session, RECORD_TABLES) == records_before


async def test_br5_records_are_tagged_and_split_by_day(
    session: AsyncSession, data_root: Path
) -> None:
    """BR5：每筆範圍內紀錄以 <record source id date> 標示，當日與前日分區。

    當日紀錄在 <current_day>，前日紀錄在各自的 <previous_day>；
    source 名稱正確，date 為所屬資料包日期。
    """
    prompt = await _prompt_for(session, data_root, "P001", SEP_03)

    current = day_blocks(prompt, "current_day")
    previous = day_blocks(prompt, "previous_day")
    assert list(current) == ["2026-09-03"]
    assert set(previous) == {"2026-09-02", "2026-09-01"}
    today = set(record_tags(current["2026-09-03"]))
    assert ("nursing_progress_note", "NPN-P001-0903-01", "2026-09-03") in today
    assert ("vital_sign", "VS-P001-0903-1", "2026-09-03") in today
    assert ("lab_result", "LAB-P001-0903-1", "2026-09-03") in today
    sep02 = set(record_tags(previous["2026-09-02"]))
    assert ("nursing_progress_note", "NPN-P001-0902-01", "2026-09-02") in sep02
    assert ("vital_sign", "VS-P001-0902-1", "2026-09-02") in sep02
    assert ("lab_result", "LAB-P001-0902-1", "2026-09-02") in sep02
    sep01 = set(record_tags(previous["2026-09-01"]))
    assert ("nursing_progress_note", "NPN-P001-0901-01", "2026-09-01") in sep01
    assert ("vital_sign", "VS-P001-0901-1", "2026-09-01") in sep01
    assert any(tag[:2] == ("tube", "TUB-P001-01") for tag in record_tags(prompt))


async def test_br5_current_records_only_in_current_block(
    session: AsyncSession, data_root: Path
) -> None:
    """BR5：當日紀錄只出現在 <current_day>；前日紀錄不在 <current_day>。"""
    prompt = await _prompt_for(session, data_root, "P001", SEP_03)

    current_ids = record_ids(day_blocks(prompt, "current_day")["2026-09-03"])
    previous_ids: set[str] = set()
    for block in day_blocks(prompt, "previous_day").values():
        previous_ids |= record_ids(block)
    assert "NPN-P001-0903-01" in current_ids
    assert "NPN-P001-0903-01" not in previous_ids
    assert "NPN-P001-0902-01" not in current_ids
    assert "NPN-P001-0901-01" not in current_ids
    tag_ids = [tag[1] for tag in record_tags(prompt)]
    assert tag_ids.count("NPN-P001-0903-01") == 1


async def test_br5_excludes_out_of_scope_dates_and_other_patients(
    session: AsyncSession, data_root: Path
) -> None:
    """BR5：範圍外日期（9/05）的紀錄與其他病患（P002）的紀錄都不出現。"""
    await _import_until(session, data_root, date(2026, 9, 5))

    prompt = await _prompt_for(session, data_root, "P001", SEP_03)

    assert "NPN-P001-0905-01" not in prompt
    assert "NPN-P001-0905-02" not in prompt
    assert "VS-P001-0905-1" not in prompt
    assert "LAB-P001-0905-1" not in prompt
    assert "P002" not in prompt
    assert "虛構病患乙" not in prompt


async def test_br5_note_content_appears_verbatim(session: AsyncSession, data_root: Path) -> None:
    """BR5：範圍內每筆護理過程紀錄的 content 原文都出現在 prompt 中。"""
    prompt = await _prompt_for(session, data_root, "P001", SEP_03)

    for day in ("20260901", "20260902", "20260903"):
        for content in _p001_contents(data_root, day):
            assert content in prompt


async def test_br5_request_metadata_and_required_elements(
    session: AsyncSession, data_root: Path
) -> None:
    """BR5：request 的 rule_code、prompt 名稱與版本、output_schema 正確。

    required_elements 等於 R02_REQUIRED_ELEMENTS，且每一條都出現在渲染結果。
    """
    llm = FakeStructuredLLM()

    await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    request = llm.requests[0]
    assert request.rule_code == "R02"
    assert request.prompt_name == "r02_copy_paste"
    assert request.prompt_version == "v1"
    assert llm.schemas[0] is R02LLMOutput
    required = request.variables["required_elements"]
    assert tuple(required) == tuple(R02_REQUIRED_ELEMENTS)
    assert len(R02_REQUIRED_ELEMENTS) > 0
    prompt = render(request)
    for element in R02_REQUIRED_ELEMENTS:
        assert element in prompt


def test_a12_prompt_template_location_and_id() -> None:
    """A12：R02 prompt 位於 app/prompts/r02_copy_paste/v1.j2。

    prompt_id("r02_copy_paste", "v1") 為 r02_copy_paste/v1。
    """
    backend_root = Path(__file__).resolve().parents[3]

    template = backend_root / "app" / "prompts" / "r02_copy_paste" / "v1.j2"

    assert template.is_file()
    assert prompt_id("r02_copy_paste", "v1") == "r02_copy_paste/v1"


async def test_a12_result_prompt_version(session: AsyncSession, data_root: Path) -> None:
    """A12／BR11：runner 執行後結果的 prompt_version 為 r02_copy_paste/v1。"""
    llm = FakeStructuredLLM()

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["prompt_version"] == "r02_copy_paste/v1"
