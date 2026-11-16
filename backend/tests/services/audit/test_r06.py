"""R06 會診資訊↔護理紀錄：可執行判斷、追蹤期限、輸入整理、輸出驗證與 prompt 渲染（虛構資料）。"""

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.enums import AvailabilityState, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceField, SourceRecord, render_records_block
from app.services.audit.rules import r06_consultation
from app.services.audit.rules.base import AuditInput
from app.services.audit.rules.r06_consultation import R06Consultation, R06Output
from app.services.llm.prompt_loader import render_prompt

_DAY = date(2026, 11, 3)
_NEXT_DAY = date(2026, 11, 4)
_CONSULT_ID = "consult-fake-0001"
_OTHER_CONSULT_ID = "consult-fake-0002"
_IN_WINDOW_NOTE_ID = "note-fake-0001"
_OTHER_CATEGORY_NOTE_ID = "note-fake-0002"
_AFTER_WINDOW_NOTE_ID = "note-fake-0003"


def _record(
    record_id: str,
    source: RawRecordCategory,
    day: date,
    fields: list[tuple[str, str]],
) -> SourceRecord:
    return SourceRecord(
        record_id=record_id,
        source=source.value,
        business_date=day,
        time_text="2026/11/03 16:22",
        recorded_at=None,
        fields=tuple(SourceField(label, value) for label, value in fields),
    )


def _consult(record_id: str = _CONSULT_ID, day: date = _DAY) -> SourceRecord:
    return _record(record_id, RawRecordCategory.CONSULTATION, day, [("類別", "胸腔內科(V:醫師甲)")])


def _note(record_id: str, day: date, category: str) -> SourceRecord:
    text = "【會診】 - 2026/11/03 16:22 胸腔內科醫師會診，建議追蹤。"
    return _record(
        record_id,
        RawRecordCategory.NURSING_PROGRESS_NOTE,
        day,
        [("類別", category), ("內容", text)],
    )


def _ctx(
    records: tuple[SourceRecord, ...],
    patient_dates: tuple[date, ...] = (_DAY, _NEXT_DAY),
    day: date = _DAY,
) -> AuditContext:
    return AuditContext(
        patient_key="FAKE-PATIENT",
        ward_code="FAKE-WARD",
        bed_code="01",
        business_date=day,
        patient_dates=patient_dates,
        admitted_at=None,
        admitted_at_text=None,
        work_checklist=WorkChecklistRead(items=[], filled_count=0, total_count=0),
        records=records,
    )


def _output(
    consultations: list[tuple[str, bool]],
    verdict: str = "NEEDS_REVIEW",
    findings: list[dict[str, Any]] | None = None,
) -> R06Output:
    payload: dict[str, Any] = {
        "verdict": verdict,
        "summary": "x",
        "findings": findings or [],
        "consultations": [
            {"record_id": record_id, "matched": matched} for record_id, matched in consultations
        ],
    }
    return R06Output.model_validate(payload)


def _rule(days: int = 1) -> R06Consultation:
    return R06Consultation(followup_days=days)


def test_rule_is_event_cycle_with_prompt_identity() -> None:
    rule = _rule()

    assert (rule.code, rule.prompt_name, rule.prompt_version) == (
        "R06",
        "r06_consultation",
        1,
    )
    assert rule.cycle.value == "event"


def test_not_applicable_when_no_consultation_on_the_day() -> None:
    ctx = _ctx((_note(_IN_WINDOW_NOTE_ID, _NEXT_DAY, "會診"),))

    availability = _rule().check_availability(ctx)

    assert availability.state == AvailabilityState.NOT_APPLICABLE
    assert availability.reason == "當日沒有會診"


def test_available_when_consultation_on_the_day() -> None:
    ctx = _ctx((_consult(),))

    assert _rule().check_availability(ctx).state == AvailabilityState.AVAILABLE


def test_window_includes_followup_categories_only_within_followup_days() -> None:
    ctx = _ctx(
        (
            _consult(),
            _note(_IN_WINDOW_NOTE_ID, _NEXT_DAY, "會診"),
            _note(_OTHER_CATEGORY_NOTE_ID, _NEXT_DAY, "一般護理"),
            _note(_AFTER_WINDOW_NOTE_ID, date(2026, 11, 5), "營養照會建議"),
        ),
        patient_dates=(_DAY, _NEXT_DAY, date(2026, 11, 5)),
    )

    audit_input = _rule(days=1).build_input(ctx)

    cited = [record.record_id for record in audit_input.records]
    assert cited == [_CONSULT_ID, _IN_WINDOW_NOTE_ID]
    assert audit_input.variables["window_start"] == "2026-11-03"
    assert audit_input.variables["window_end"] == "2026-11-04"


def test_window_counts_nutrition_consult_category_as_followup() -> None:
    ctx = _ctx((_consult(), _note(_IN_WINDOW_NOTE_ID, _DAY, "營養照會建議")))

    audit_input = _rule(days=0).build_input(ctx)

    assert [record.record_id for record in audit_input.records] == [
        _CONSULT_ID,
        _IN_WINDOW_NOTE_ID,
    ]


def test_followup_marked_complete_when_last_data_day_reaches_window_end() -> None:
    ctx = _ctx((_consult(),), patient_dates=(_DAY, _NEXT_DAY))

    audit_input = _rule(days=1).build_input(ctx)

    assert audit_input.variables["followup_data_status"] == "已到齊"
    assert audit_input.variables["last_data_date"] == "2026-11-04"


def test_followup_marked_incomplete_when_last_data_day_is_before_window_end() -> None:
    ctx = _ctx((_consult(),), patient_dates=(_DAY,))

    audit_input = _rule(days=1).build_input(ctx)

    assert audit_input.variables["followup_data_status"] == "尚未到齊"


def test_consult_block_lists_time_and_department_per_consultation() -> None:
    ctx = _ctx((_consult(), _consult(_OTHER_CONSULT_ID, _DAY)))

    block = _rule().build_input(ctx).variables["consult_block"]

    assert f"record_id={_CONSULT_ID}" in block
    assert f"record_id={_OTHER_CONSULT_ID}" in block
    assert "科別：胸腔內科(V:醫師甲)" in block


def test_default_followup_days_come_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(AUDIT_CONSULT_FOLLOWUP_DAYS=2)
    monkeypatch.setattr(r06_consultation, "get_settings", lambda: fake)
    ctx = _ctx((_consult(),), patient_dates=(_DAY, _NEXT_DAY))

    audit_input = R06Consultation().build_input(ctx)

    assert audit_input.variables["window_end"] == "2026-11-05"


def test_prompt_renders_status_and_records() -> None:
    ctx = _ctx((_consult(), _note(_IN_WINDOW_NOTE_ID, _NEXT_DAY, "會診")), patient_dates=(_DAY,))
    audit_input = _rule().build_input(ctx)
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt("r06_consultation", 1, variables)

    assert "尚未到齊" in text
    assert f'id="{_CONSULT_ID}"' in text
    assert f'id="{_IN_WINDOW_NOTE_ID}"' in text
    assert "2026-11-04" in text


def test_valid_output_passes_when_every_consultation_is_answered() -> None:
    audit_input = AuditInput(
        variables={"followup_data_status": "已到齊"},
        records=(_consult(),),
    )

    _rule().validate_output(_output([(_CONSULT_ID, True)], verdict="PASS"), audit_input)


def test_missing_consultation_answer_is_rejected() -> None:
    audit_input = AuditInput(
        variables={"followup_data_status": "已到齊"},
        records=(_consult(), _consult(_OTHER_CONSULT_ID)),
    )

    with pytest.raises(LLMOutputError):
        _rule().validate_output(_output([(_CONSULT_ID, True)]), audit_input)


def test_unknown_consultation_id_is_rejected() -> None:
    audit_input = AuditInput(
        variables={"followup_data_status": "已到齊"},
        records=(_consult(),),
    )

    with pytest.raises(LLMOutputError):
        _rule().validate_output(_output([("not-in-input", True)]), audit_input)


def test_duplicated_consultation_answer_is_rejected() -> None:
    audit_input = AuditInput(
        variables={"followup_data_status": "已到齊"},
        records=(_consult(),),
    )

    with pytest.raises(LLMOutputError):
        _rule().validate_output(_output([(_CONSULT_ID, True), (_CONSULT_ID, False)]), audit_input)


def test_unmatched_consultation_cannot_be_pass() -> None:
    audit_input = AuditInput(
        variables={"followup_data_status": "已到齊"},
        records=(_consult(),),
    )

    with pytest.raises(LLMOutputError):
        _rule().validate_output(_output([(_CONSULT_ID, False)], verdict="PASS"), audit_input)


def test_warning_is_rejected_while_followup_data_incomplete() -> None:
    audit_input = AuditInput(
        variables={"followup_data_status": "尚未到齊"},
        records=(_consult(),),
    )
    finding = {"item": "胸腔內科", "verdict": "WARNING", "message": "x", "evidence": []}
    output = _output([(_CONSULT_ID, False)], verdict="WARNING", findings=[finding])

    with pytest.raises(LLMOutputError):
        _rule().validate_output(output, audit_input)


def test_needs_review_is_allowed_while_followup_data_incomplete() -> None:
    audit_input = AuditInput(
        variables={"followup_data_status": "尚未到齊"},
        records=(_consult(),),
    )

    _rule().validate_output(_output([(_CONSULT_ID, False)], verdict="NEEDS_REVIEW"), audit_input)


def test_non_r06_output_is_rejected() -> None:
    plain = RuleOutput(verdict="PASS", summary="x", findings=[])
    audit_input = AuditInput(variables={"followup_data_status": "已到齊"})

    with pytest.raises(LLMOutputError):
        _rule().validate_output(plain, audit_input)
