"""R02 異常行為測試：E6（無紀錄）、E7（LLM 失敗）、E8（schema）、E9、E11。"""

from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from r02_support import (
    FakeStructuredLLM,
    assert_no_forbidden_words,
    count_rows,
    edit_json,
    patient_file,
    read_json,
    render,
    run_r02,
    set_notes,
    write_json,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LLMOutputError
from app.services.audit.rules.r02_copy_paste import R02LLMOutput

SEP_03 = date(2026, 9, 3)
NO_TODAY_MESSAGE = "今日未見護理過程紀錄，無法比對，請確認"
NO_PREVIOUS_MESSAGE = "前日未見護理過程紀錄，無法比對，請確認"
LLM_FAILED_MESSAGE = "系統無法完成判定，請稍後重試或人工確認"


def _break_spo2(data: dict[str, Any]) -> None:
    data["vital_signs"][0]["spo2"] = "abc"


# ---------- E6 ----------


async def test_e6_no_current_notes_needs_review_without_llm(
    session: AsyncSession, data_root: Path
) -> None:
    """E6：當日護理過程紀錄為 [] → NEEDS_REVIEW，不呼叫 LLM。

    訊息為「今日未見護理過程紀錄，無法比對，請確認」，結果仍寫入。
    """
    set_notes(data_root, "20260903", "P001", [])
    llm = FakeStructuredLLM()

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["verdict"] == "NEEDS_REVIEW"
    assert result["message"] == NO_TODAY_MESSAGE
    assert llm.calls == 0
    assert await count_rows(session, "audit_findings") == 1


async def test_e6_no_previous_notes_needs_review_without_llm(
    session: AsyncSession, data_root: Path
) -> None:
    """E6：前 2 個資料日（9/02、9/01）都沒有護理過程紀錄。

    → NEEDS_REVIEW，訊息「前日未見護理過程紀錄…」，不呼叫 LLM，結果仍寫入。
    """
    set_notes(data_root, "20260902", "P001", [])
    set_notes(data_root, "20260901", "P001", [])
    llm = FakeStructuredLLM()

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["verdict"] == "NEEDS_REVIEW"
    assert result["message"] == NO_PREVIOUS_MESSAGE
    assert llm.calls == 0
    assert await count_rows(session, "audit_findings") == 1


async def test_e6_one_previous_day_with_notes_calls_llm(
    session: AsyncSession, data_root: Path
) -> None:
    """E6 邊界：前 2 日中只要有 1 日有紀錄（9/02）→ 會呼叫 LLM 一次。"""
    set_notes(data_root, "20260901", "P001", [])
    llm = FakeStructuredLLM()

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert llm.calls == 1
    assert result["message"] != NO_PREVIOUS_MESSAGE


# ---------- E7 ----------


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(LLMOutputError("輸出不符格式"), id="E7-llm-output-error"),
        pytest.param(TimeoutError(), id="E7-timeout"),
        pytest.param(ConnectionError(), id="E7-connection-error"),
    ],
)
async def test_e7_llm_failure_needs_review_and_is_saved(
    session: AsyncSession, data_root: Path, error: BaseException
) -> None:
    """E7：gateway 拋 LLMOutputError、逾時或連線錯誤 → NEEDS_REVIEW，絕不是 PASS。

    note_similarities 為空；結果仍寫入 audit_findings。
    """
    llm = FakeStructuredLLM(error=error)

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["verdict"] == "NEEDS_REVIEW"
    assert result["verdict"] != "PASS"
    assert result["message"] == LLM_FAILED_MESSAGE
    assert result["note_similarities"] == []
    assert await count_rows(session, "audit_findings") == 1
    assert_no_forbidden_words(result["message"])


# ---------- E8（schema 層） ----------


def _valid_payload() -> dict[str, Any]:
    return {
        "verdict": "WARNING",
        "notes": [
            {
                "record_id": "NPN-X-01",
                "similar_record_id": "NPN-X-00",
                "similarity_percent": 50,
                "issue_types": ["copy"],
            }
        ],
        "evidence": [],
    }


def _with_percent(value: float) -> dict[str, Any]:
    payload = _valid_payload()
    payload["notes"][0]["similarity_percent"] = value
    return payload


def _with_verdict(value: str) -> dict[str, Any]:
    payload = _valid_payload()
    payload["verdict"] = value
    return payload


def _without_top(key: str) -> dict[str, Any]:
    payload = _valid_payload()
    del payload[key]
    return payload


def _without_note_field(key: str) -> dict[str, Any]:
    payload = _valid_payload()
    del payload["notes"][0][key]
    return payload


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(_with_percent(-0.1), id="E8-percent-below-0"),
        pytest.param(_with_percent(100.1), id="E8-percent-above-100"),
        pytest.param(_with_verdict("ERROR"), id="E8-verdict-ERROR"),
        pytest.param(_with_verdict("NEEDS_REVIEW"), id="E8-verdict-NEEDS_REVIEW"),
        pytest.param(_without_top("notes"), id="E8-missing-notes"),
        pytest.param(_without_note_field("similarity_percent"), id="E8-missing-similarity"),
        pytest.param(_without_note_field("issue_types"), id="E8-missing-issue-types"),
        pytest.param(_without_note_field("similar_record_id"), id="E8-missing-similar-record"),
    ],
)
def test_e8_invalid_llm_output_fails_schema(payload: dict[str, Any]) -> None:
    """E8：輸出不符 schema → ValidationError。

    similarity_percent 超出 0～100、verdict 不是 PASS／WARNING、缺必要欄位。
    """
    with pytest.raises(ValidationError):
        R02LLMOutput.model_validate(payload)


@pytest.mark.parametrize(
    "value",
    [pytest.param(0, id="E8-boundary-0"), pytest.param(100, id="E8-boundary-100")],
)
def test_e8_similarity_bounds_are_valid(value: float) -> None:
    """E8 邊界：similarity_percent 為 0、100 合法。"""
    parsed = R02LLMOutput.model_validate(_with_percent(value))

    assert parsed.notes[0].similarity_percent == pytest.approx(value)


def test_e8_nullable_fields_accept_none() -> None:
    """E8：similar_record_id、similarity_percent 明確給 None 合法；PASS 合法。"""
    payload = _valid_payload()
    payload["verdict"] = "PASS"
    payload["notes"][0]["similar_record_id"] = None
    payload["notes"][0]["similarity_percent"] = None

    parsed = R02LLMOutput.model_validate(payload)

    assert parsed.notes[0].similar_record_id is None
    assert parsed.notes[0].similarity_percent is None


# ---------- E9 ----------


async def test_e9_invalid_file_in_scope_needs_review_without_llm(
    session: AsyncSession, data_root: Path
) -> None:
    """E9：範圍內 9/02 的 P001 檔驗證失敗 → 稽核 9/03 為 NEEDS_REVIEW。

    訊息為「9/02 資料格式不符，無法判定，請確認」，不呼叫 LLM。
    """
    edit_json(patient_file(data_root, "20260902", "P001"), _break_spo2)
    llm = FakeStructuredLLM()

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["verdict"] == "NEEDS_REVIEW"
    assert result["message"] == "9/02 資料格式不符，無法判定，請確認"
    assert llm.calls == 0


async def test_e9_other_patient_in_same_batch_still_audited(
    session: AsyncSession, data_root: Path
) -> None:
    """E9：同批其他病患檔照常匯入 → 稽核 P002 9/02 時 prompt 含其 9/02 紀錄。"""
    edit_json(patient_file(data_root, "20260902", "P001"), _break_spo2)
    llm = FakeStructuredLLM()

    await run_r02(session, data_root, llm, patient_key="P002", business_date=date(2026, 9, 2))

    assert llm.calls == 1
    assert "NPN-P002-0902-01" in render(llm.requests[0])


# ---------- E11 ----------


async def test_e11_out_of_root_file_needs_review_without_llm(
    session: AsyncSession, data_root: Path, tmp_path: Path
) -> None:
    """E11：9/03 manifest 中 P001 的 file 為 ../../outside.json → 視為 E9。

    - ingestion_errors 有紀錄、RAW_DATA_DIR 下沒有 outside.json
    - 稽核 P001 9/03 為 NEEDS_REVIEW，訊息「9/03 資料格式不符…」
    - 不呼叫 LLM
    """
    outside = read_json(data_root / "20260903" / "P001.json")
    write_json(tmp_path / "outside.json", outside)

    def _point_outside(manifest: dict[str, Any]) -> None:
        manifest["patients"][0]["file"] = "../../outside.json"

    edit_json(data_root / "20260903" / "manifest.json", _point_outside)
    llm = FakeStructuredLLM()

    result = await run_r02(session, data_root, llm, patient_key="P001", business_date=SEP_03)

    assert result["verdict"] == "NEEDS_REVIEW"
    assert result["message"] == "9/03 資料格式不符，無法判定，請確認"
    assert llm.calls == 0
    assert await count_rows(session, "ingestion_errors") >= 1
    raw_root = tmp_path / "raw"
    assert not any(path.name == "outside.json" for path in raw_root.rglob("*"))
