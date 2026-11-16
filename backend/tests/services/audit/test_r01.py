"""R01 入院經過↔入院身體評估：可執行判斷、輸入整理、專屬輸出驗證與 prompt 渲染（虛構資料）。"""

import dataclasses
from datetime import date
from typing import Any

import pytest

from app.core.enums import AvailabilityState, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceField, SourceRecord, render_records_block
from app.services.audit.rules.base import AuditInput
from app.services.audit.rules.r01_admission_course import (
    REQUIRED_ELEMENTS,
    R01AdmissionCourse,
    R01Output,
)
from app.services.llm.prompt_loader import render_prompt

RULE = R01AdmissionCourse()
_DAY = date(2026, 11, 3)
_COURSE_ID = "course-fake-0001"
_ASSESSMENT_ID = "assessment-fake-0001"

_ALL_MENTIONED = [{"element": "處理", "mentioned": True}]


def _record(record_id: str, source: str, fields: list[tuple[str, str]]) -> SourceRecord:
    return SourceRecord(
        record_id=record_id,
        source=source,
        business_date=_DAY,
        time_text="2026/11/03 08:00",
        recorded_at=None,
        fields=tuple(SourceField(label, value) for label, value in fields),
    )


def _course() -> SourceRecord:
    text = "2026/11/03 清晨開始胸悶、胸痛，於急診就醫，給予藥物處理，因此住院。"
    return _record(_COURSE_ID, RawRecordCategory.ADMISSION_COURSE, [("內容", text)])


def _assessment() -> SourceRecord:
    return _record(
        _ASSESSMENT_ID,
        RawRecordCategory.ADMISSION_ASSESSMENT,
        [("胸痛", "正常"), ("呼吸音", "清")],
    )


def _ctx(*records: SourceRecord) -> AuditContext:
    return AuditContext(
        patient_key="FAKE-PATIENT",
        ward_code="FAKE-WARD",
        bed_code="01",
        business_date=_DAY,
        patient_dates=(_DAY,),
        admitted_at=None,
        admitted_at_text="2026/11/03 08:00",
        work_checklist=WorkChecklistRead(items=[], filled_count=0, total_count=0),
        records=tuple(records),
    )


def _output(elements: list[tuple[str, bool]], verdict: str = "WARNING") -> R01Output:
    payload: dict[str, Any] = {
        "verdict": verdict,
        "summary": "x",
        "findings": [],
        "elements": [{"element": name, "mentioned": mentioned} for name, mentioned in elements],
    }
    return R01Output.model_validate(payload)


ALL_MENTIONED = [(name, True) for name in REQUIRED_ELEMENTS]


def test_rule_is_one_time_per_admission_with_prompt_identity() -> None:
    assert (RULE.code, RULE.prompt_name, RULE.prompt_version) == (
        "R01",
        "r01_admission_course",
        1,
    )


def test_available_when_course_and_assessment_exist() -> None:
    assert RULE.check_availability(_ctx(_course(), _assessment())).state == (
        AvailabilityState.AVAILABLE
    )


def test_data_unavailable_without_course_names_the_missing_item() -> None:
    availability = RULE.check_availability(_ctx(_assessment()))

    assert availability.state == AvailabilityState.DATA_UNAVAILABLE
    assert availability.reason is not None
    assert "入院經過" in availability.reason


def test_data_unavailable_without_assessment_names_the_missing_item() -> None:
    availability = RULE.check_availability(_ctx(_course()))

    assert availability.state == AvailabilityState.DATA_UNAVAILABLE
    assert availability.reason is not None
    assert "入院身體評估" in availability.reason


def test_build_input_cites_course_and_all_assessment_records() -> None:
    audit_input = RULE.build_input(_ctx(_course(), _assessment()))

    assert [record.record_id for record in audit_input.records] == [_COURSE_ID, _ASSESSMENT_ID]
    assert audit_input.variables["admitted_at_text"] == "2026/11/03 08:00"
    assert (
        audit_input.variables["required_elements_block"].count("\n") == len(REQUIRED_ELEMENTS) - 1
    )


def test_build_input_marks_missing_admission_time_as_not_provided() -> None:
    ctx = dataclasses.replace(_ctx(_course(), _assessment()), admitted_at_text=None)

    audit_input = RULE.build_input(ctx)

    assert audit_input.variables["admitted_at_text"] == "院方未提供"


def test_prompt_renders_elements_and_records() -> None:
    audit_input = RULE.build_input(_ctx(_course(), _assessment()))
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    for name in REQUIRED_ELEMENTS:
        assert f"- {name}" in text
    assert f'id="{_COURSE_ID}"' in text
    assert f'source="{RawRecordCategory.ADMISSION_ASSESSMENT.value}"' in text
    assert "入院時間：2026/11/03 08:00" in text


def test_valid_output_passes_and_keeps_elements_as_details() -> None:
    parsed = _output(ALL_MENTIONED)

    RULE.validate_output(parsed, AuditInput(variables={}))

    details = parsed.model_dump(exclude=set(RuleOutput.model_fields))
    assert details["elements"][0] == {"element": REQUIRED_ELEMENTS[0], "mentioned": True}


def test_missing_element_in_reply_is_rejected() -> None:
    parsed = _output(ALL_MENTIONED[:-1])

    with pytest.raises(LLMOutputError):
        RULE.validate_output(parsed, AuditInput(variables={}))


def test_unknown_element_name_is_rejected() -> None:
    names = [*ALL_MENTIONED[:-1], ("其他", True)]

    with pytest.raises(LLMOutputError):
        RULE.validate_output(_output(names), AuditInput(variables={}))


def test_duplicated_element_name_is_rejected() -> None:
    names = [*ALL_MENTIONED[:-1], (REQUIRED_ELEMENTS[0], True)]

    with pytest.raises(LLMOutputError):
        RULE.validate_output(_output(names), AuditInput(variables={}))


def test_pass_with_unmentioned_element_is_rejected() -> None:
    names = [*ALL_MENTIONED[:-1], (REQUIRED_ELEMENTS[-1], False)]

    with pytest.raises(LLMOutputError):
        RULE.validate_output(_output(names, verdict="PASS"), AuditInput(variables={}))


def test_non_r01_output_is_rejected() -> None:
    plain = RuleOutput(verdict="PASS", summary="x", findings=[])

    with pytest.raises(LLMOutputError):
        RULE.validate_output(plain, AuditInput(variables={}))


def test_unmentioned_elements_get_not_recorded_label() -> None:
    details = {"elements": [{"element": "住院原因", "mentioned": False}, *_ALL_MENTIONED]}

    assert R01AdmissionCourse().finding_labels(details) == {"住院原因": "未見紀錄"}


def test_no_labels_without_details() -> None:
    assert R01AdmissionCourse().finding_labels(None) == {}
