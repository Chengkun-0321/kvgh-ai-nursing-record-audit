"""R02 結果測試：BR6（note_similarities）、BR7（判定）、BR8（Evidence）、BR11。"""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from r02_support import (
    P001_0903_EXCERPT,
    P001_0905_01_EXCERPT,
    FakeStructuredLLM,
    evidence,
    llm_output,
    note,
    run_r02,
)
from sqlalchemy.ext.asyncio import AsyncSession

SEP_03 = date(2026, 9, 3)
SEP_05 = date(2026, 9, 5)
NOTE_0903 = "NPN-P001-0903-01"
NOTE_0902 = "NPN-P001-0902-01"
NOTE_0905_1 = "NPN-P001-0905-01"
NOTE_0905_2 = "NPN-P001-0905-02"
VALID_EVIDENCE = evidence(NOTE_0903, P001_0903_EXCERPT)


async def _run(
    session: AsyncSession,
    root: Path,
    output: dict[str, Any],
    business_date: date = SEP_03,
) -> dict[str, Any]:
    llm = FakeStructuredLLM(output=output)
    return await run_r02(session, root, llm, patient_key="P001", business_date=business_date)


def _similarity(result: dict[str, Any], record_id: str) -> dict[str, Any]:
    items = [s for s in result["note_similarities"] if s["record_id"] == record_id]
    assert len(items) == 1, f"{record_id} 應恰好有一筆 note_similarities"
    return items[0]


# ---------- BR6 ----------


async def test_br6_one_similarity_per_current_note(session: AsyncSession, data_root: Path) -> None:
    """BR6：當日 2 筆護理過程紀錄 → note_similarities 恰好 2 項，record_id 相同。"""
    output = llm_output(
        "PASS",
        notes=[
            note(NOTE_0905_1, similar_record_id=NOTE_0903, similarity_percent=40),
            note(NOTE_0905_2),
        ],
    )

    result = await _run(session, data_root, output, SEP_05)

    ids = [item["record_id"] for item in result["note_similarities"]]
    assert sorted(ids) == [NOTE_0905_1, NOTE_0905_2]


async def test_br6_similar_business_date_is_looked_up_by_program(
    session: AsyncSession, data_root: Path
) -> None:
    """BR6：similar_business_date 由程式依 similar_record_id 查出。

    LLM 多回一個錯誤的 similar_business_date（extra 被忽略）也不採用。
    """
    llm_note = note(NOTE_0903, similar_record_id=NOTE_0902, similarity_percent=50)
    llm_note["similar_business_date"] = "2026-08-31"
    output = llm_output("PASS", notes=[llm_note])

    result = await _run(session, data_root, output)

    item = _similarity(result, NOTE_0903)
    assert item["similar_record_id"] == NOTE_0902
    assert item["similar_business_date"] == "2026-09-02"


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        pytest.param(97.65, 97.7, id="BR6-97.65-half-up"),
        pytest.param(97.64, 97.6, id="BR6-97.64-down"),
        pytest.param(99.95, 100.0, id="BR6-99.95-to-100"),
        pytest.param(100, 100.0, id="BR6-upper-bound-100"),
        pytest.param(0, 0.0, id="BR6-zero"),
    ],
)
async def test_br6_similarity_rounds_half_up_to_one_decimal(
    session: AsyncSession, data_root: Path, given: float, expected: float
) -> None:
    """BR6：similarity_percent 以 ROUND_HALF_UP 取到小數 1 位（含上限與 0）。"""
    llm_note = note(NOTE_0903, similar_record_id=NOTE_0902, similarity_percent=given)
    output = llm_output("PASS", notes=[llm_note])

    result = await _run(session, data_root, output)

    actual = _similarity(result, NOTE_0903)["similarity_percent"]
    assert actual == pytest.approx(expected, abs=1e-9)


async def test_br6_no_similar_record_gives_three_nulls(
    session: AsyncSession, data_root: Path
) -> None:
    """BR6：LLM 認為沒有相似紀錄 → 三個 similar 欄位都是 None。"""
    output = llm_output("PASS", notes=[note(NOTE_0903)])

    result = await _run(session, data_root, output)

    item = _similarity(result, NOTE_0903)
    assert item["similar_record_id"] is None
    assert item["similar_business_date"] is None
    assert item["similarity_percent"] is None


async def test_br6_missing_note_from_llm_still_listed(
    session: AsyncSession, data_root: Path
) -> None:
    """BR6：LLM 漏回某筆當日紀錄 → 結果仍有該筆，similar_* 為 None。"""
    llm_note = note(NOTE_0905_1, similar_record_id=NOTE_0902, similarity_percent=30)
    output = llm_output("PASS", notes=[llm_note])

    result = await _run(session, data_root, output, SEP_05)

    item = _similarity(result, NOTE_0905_2)
    assert item["similar_record_id"] is None
    assert item["similar_business_date"] is None
    assert item["similarity_percent"] is None
    assert len(result["note_similarities"]) == 2


async def test_br6_recorded_at_comes_from_note(session: AsyncSession, data_root: Path) -> None:
    """BR6：note_similarities 的 recorded_at 為該筆紀錄時間（比較時間點）。"""
    llm_note = note(NOTE_0903, similar_record_id=NOTE_0902, similarity_percent=50)
    output = llm_output("PASS", notes=[llm_note])

    result = await _run(session, data_root, output)

    raw = _similarity(result, NOTE_0903)["recorded_at"]
    recorded_at = datetime.fromisoformat(raw)
    expected = datetime.fromisoformat("2026-09-03T09:30:00+08:00")
    assert recorded_at.tzinfo is not None
    assert recorded_at == expected


# ---------- BR7 ----------

_INVALID_EVIDENCES = [
    evidence(NOTE_0903, "完全不存在的虛構片段"),
    evidence("NPN-FAKE-01", P001_0903_EXCERPT),
]


@pytest.mark.parametrize(
    ("verdict", "evidences", "expected"),
    [
        pytest.param("WARNING", [VALID_EVIDENCE], "WARNING", id="BR7-warning-1-evidence"),
        pytest.param("WARNING", [], "NEEDS_REVIEW", id="BR7-warning-0-evidence"),
        pytest.param(
            "WARNING",
            _INVALID_EVIDENCES,
            "NEEDS_REVIEW",
            id="BR7-warning-all-evidence-invalid",
        ),
        pytest.param("PASS", [], "PASS", id="BR7-pass-0-evidence"),
    ],
)
async def test_br7_verdict_depends_on_valid_evidence(
    *,
    session: AsyncSession,
    data_root: Path,
    verdict: str,
    evidences: list[dict[str, Any]],
    expected: str,
) -> None:
    """BR7：WARNING 驗證後至少剩 1 筆 Evidence 才成立，否則 NEEDS_REVIEW。

    PASS 可以沒有 Evidence；不產生 ERROR；engine 一律為 llm。
    """
    issues = ["copy"] if verdict == "WARNING" else []
    notes = [
        note(NOTE_0903, similar_record_id=NOTE_0902, similarity_percent=98, issue_types=issues)
    ]
    output = llm_output(verdict, notes=notes, evidences=evidences)

    result = await _run(session, data_root, output)

    assert result["verdict"] == expected
    assert result["verdict"] != "ERROR"
    assert result["engine"] == "llm"


# ---------- BR8 ----------


async def _warning_with(
    session: AsyncSession, root: Path, evidences: list[dict[str, Any]]
) -> dict[str, Any]:
    notes = [
        note(NOTE_0903, similar_record_id=NOTE_0902, similarity_percent=98, issue_types=["copy"])
    ]
    output = llm_output("WARNING", notes=notes, evidences=evidences)
    return await _run(session, root, output)


async def test_br8_evidence_with_unknown_record_id_is_dropped(
    session: AsyncSession, data_root: Path
) -> None:
    """BR8：record_id 不在送出資料中的 Evidence（NPN-FAKE-01）被丟棄。"""
    fake = evidence("NPN-FAKE-01", P001_0903_EXCERPT)

    result = await _warning_with(session, data_root, [VALID_EVIDENCE, fake])

    assert [item["record_id"] for item in result["evidence"]] == [NOTE_0903]
    assert result["verdict"] == "WARNING"


async def test_br8_excerpt_whitespace_is_ignored(session: AsyncSession, data_root: Path) -> None:
    """BR8：excerpt 多了空白、換行、全形空白，去空白後是原文子字串 → 保留。"""
    spaced = evidence(NOTE_0903, " 主訴傷口 疼痛\n分數　三分 ")

    result = await _warning_with(session, data_root, [spaced])

    assert result["verdict"] == "WARNING"
    assert [item["record_id"] for item in result["evidence"]] == [NOTE_0903]


@pytest.mark.parametrize(
    "excerpt",
    [
        pytest.param("病人主訴胸悶喘不過氣", id="BR8-not-substring"),
        pytest.param("  ", id="BR8-blank-after-strip"),
    ],
)
async def test_br8_invalid_excerpt_is_dropped(
    session: AsyncSession, data_root: Path, excerpt: str
) -> None:
    """BR8：excerpt 不是原文子字串、或去空白後為空字串 → 丟棄。"""
    invalid = [evidence(NOTE_0903, excerpt)]

    result = await _warning_with(session, data_root, invalid)

    assert result["evidence"] == []
    assert result["verdict"] == "NEEDS_REVIEW"


async def test_br8_kept_evidence_source_is_filled_by_program(
    session: AsyncSession, data_root: Path
) -> None:
    """BR8：保留的 Evidence 的 source 由程式依紀錄類型填入。

    護理過程紀錄為 nursing_progress_note，record_id 正確。
    """
    result = await _warning_with(session, data_root, [VALID_EVIDENCE])

    assert len(result["evidence"]) == 1
    kept = result["evidence"][0]
    assert kept["source"] == "nursing_progress_note"
    assert kept["record_id"] == NOTE_0903


async def test_br8_similarity_with_unknown_record_id_is_dropped(
    session: AsyncSession, data_root: Path
) -> None:
    """BR8：LLM 回的 note record_id 不存在（NPN-FAKE-01）→ 結果中沒有它。

    項目數仍等於當日紀錄數（1）。
    """
    notes = [
        note("NPN-FAKE-01", similar_record_id=NOTE_0902, similarity_percent=90),
        note(NOTE_0903),
    ]

    result = await _run(session, data_root, llm_output("PASS", notes=notes))

    ids = [item["record_id"] for item in result["note_similarities"]]
    assert "NPN-FAKE-01" not in ids
    assert ids == [NOTE_0903]


async def test_br8_similarity_with_unknown_similar_record_is_dropped(
    session: AsyncSession, data_root: Path
) -> None:
    """BR8：similar_record_id 不存在（NPN-FAKE-02）→ 沒有項目引用它。

    該筆當日紀錄的項目仍存在，similar_record_id 為 None。
    """
    notes = [note(NOTE_0903, similar_record_id="NPN-FAKE-02", similarity_percent=95)]

    result = await _run(session, data_root, llm_output("PASS", notes=notes))

    referenced = [item["similar_record_id"] for item in result["note_similarities"]]
    assert "NPN-FAKE-02" not in referenced
    assert _similarity(result, NOTE_0903)["similar_record_id"] is None


async def test_br8_evidence_on_one_of_two_current_notes_is_kept(
    session: AsyncSession, data_root: Path
) -> None:
    """BR8：9/05 的 Evidence 引用當日第一筆紀錄的原文片段 → 保留。"""
    notes = [
        note(
            NOTE_0905_1,
            similar_record_id=NOTE_0903,
            similarity_percent=92,
            issue_types=["copy"],
        ),
        note(NOTE_0905_2),
    ]
    evidences = [evidence(NOTE_0905_1, P001_0905_01_EXCERPT)]
    output = llm_output("WARNING", notes=notes, evidences=evidences)

    result = await _run(session, data_root, output, SEP_05)

    assert result["verdict"] == "WARNING"
    assert [item["record_id"] for item in result["evidence"]] == [NOTE_0905_1]


# ---------- BR11 ----------


async def test_br11_result_records_model_and_versions(
    session: AsyncSession, data_root: Path
) -> None:
    """BR11：結果記錄 model、prompt_version、system_prompt_version、audited_at。"""
    llm = FakeStructuredLLM(system_prompt_version=7)

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["model"] == "fake-model"
    assert result["prompt_version"] == "r02_copy_paste/v1"
    assert result["system_prompt_version"] == 7
    assert datetime.fromisoformat(result["audited_at"]).tzinfo is not None


async def test_br11_system_prompt_version_none_is_kept(
    session: AsyncSession, data_root: Path
) -> None:
    """BR11：gateway 回傳的 system_prompt_version 為 None 時，結果也是 None。"""
    llm = FakeStructuredLLM(system_prompt_version=None)

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["system_prompt_version"] is None
