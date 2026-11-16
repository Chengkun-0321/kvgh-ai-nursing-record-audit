"""R03 範本規則：可執行判斷、輸入整理、專屬輸出驗證，與 prompt 渲染。"""

import dataclasses
from datetime import date
from typing import Any

import pytest

from app.core.enums import AvailabilityState
from app.core.exceptions import LLMOutputError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext, build_audit_context
from app.services.audit.records import render_records_block
from app.services.audit.rules.base import AuditInput
from app.services.audit.rules.r03_admission_completeness import (
    R03AdmissionCompleteness,
    R03Output,
)
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm.prompt_loader import render_prompt
from tests.hospital_data_samples import AUDIT_P3_KEY

RULE = R03AdmissionCompleteness()


@pytest.fixture
async def admission_ctx(audit_hospital_data_source: HospitalDataSource) -> AuditContext:
    ctx = await build_audit_context(audit_hospital_data_source, AUDIT_P3_KEY, None)
    return ctx.for_date(date(2025, 12, 31))


def test_rule_is_one_time_per_admission_with_prompt_identity() -> None:
    assert (RULE.code, RULE.prompt_name, RULE.prompt_version) == (
        "R03",
        "r03_admission_completeness",
        1,
    )


async def test_available_when_checklist_exists(admission_ctx: AuditContext) -> None:
    assert RULE.check_availability(admission_ctx).state == AvailabilityState.AVAILABLE


async def test_data_unavailable_without_checklist(admission_ctx: AuditContext) -> None:
    empty = WorkChecklistRead(items=[], filled_count=0, total_count=0)
    ctx = dataclasses.replace(admission_ctx, work_checklist=empty)

    availability = RULE.check_availability(ctx)

    assert availability.state == AvailabilityState.DATA_UNAVAILABLE
    assert availability.reason is not None


async def test_build_input_cites_checklist_and_admission_course(
    admission_ctx: AuditContext,
) -> None:
    audit_input = RULE.build_input(admission_ctx)

    assert audit_input.records[0].source == "work_checklist"
    assert audit_input.records[0].record_id.startswith("work_checklist-")
    assert [record.source for record in audit_input.records[1:]] == ["admission_course"]
    assert "個人病史：沒有填寫" in audit_input.variables["checklist_block"]
    assert audit_input.variables["admission_course_status"] == "有內容"


async def test_prompt_renders_with_build_input_variables(admission_ctx: AuditContext) -> None:
    audit_input = RULE.build_input(admission_ctx)
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    assert "心靈社會（對應工作清單欄位：心理評估）" in text
    assert "住院經過（對應院方的入院經過紀錄）" in text
    assert 'source="work_checklist"' in text


def test_output_items_outside_required_list_are_rejected() -> None:
    output: dict[str, Any] = {
        "verdict": "WARNING",
        "summary": "x",
        "findings": [{"item": "不存在的項目", "verdict": "WARNING", "message": "x"}],
        "incomplete_items": [],
    }
    parsed = R03Output.model_validate(output)

    with pytest.raises(LLMOutputError):
        RULE.validate_output(parsed, AuditInput(variables={}))


def test_valid_output_passes_and_keeps_extra_fields() -> None:
    parsed = R03Output.model_validate(
        {
            "verdict": "WARNING",
            "summary": "x",
            "findings": [{"item": "個人病史", "verdict": "WARNING", "message": "x"}],
            "incomplete_items": ["個人病史"],
        }
    )
    assert isinstance(parsed, RuleOutput)

    RULE.validate_output(parsed, AuditInput(variables={}))
    assert parsed.model_dump(exclude=set(RuleOutput.model_fields)) == {
        "incomplete_items": ["個人病史"]
    }
