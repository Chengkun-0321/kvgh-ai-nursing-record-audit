"""R07 預留規則：不可執行判斷、輸入整理（虛構資料）、輸出驗證與 prompt 渲染。"""

from datetime import date
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditCycle, AuditRunStatus, AvailabilityState, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.llm_structured import LLMRequest, RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceField, SourceRecord, render_records_block
from app.services.audit.rules.base import AuditInput
from app.services.audit.rules.r07_medication_followup import (
    RESPONSE_ITEM,
    R07MedicationFollowup,
    R07Output,
)
from app.services.audit.service import AuditService
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm import gateway
from app.services.llm.prompt_loader import render_prompt
from tests.hospital_data_samples import AUDIT_P3_KEY

RULE = R07MedicationFollowup()
DAY = date(2026, 1, 2)
PREVIOUS_DAY = date(2026, 1, 1)
SELECTED_DAY = date(2026, 1, 2)
MEDICATION = RawRecordCategory.MEDICATION_ORDER.value
NURSING = RawRecordCategory.NURSING_PROGRESS_NOTE.value
VITAL = RawRecordCategory.VITAL_SIGN.value
LAB = RawRecordCategory.LAB_RESULT.value


def _record(
    record_id: str,
    source: str,
    fields: list[tuple[str, str]],
    day: date = DAY,
) -> SourceRecord:
    return SourceRecord(
        record_id=record_id,
        source=source,
        business_date=day,
        time_text="",
        recorded_at=None,
        fields=tuple(SourceField(label, value) for label, value in fields),
    )


def _ctx(records: tuple[SourceRecord, ...]) -> AuditContext:
    """虛構的病患快照，不讀取院方檔案。"""
    return AuditContext(
        patient_key="TEST-R07",
        ward_code="TEST",
        bed_code="00",
        business_date=DAY,
        patient_dates=(PREVIOUS_DAY, DAY),
        admitted_at=None,
        admitted_at_text=None,
        work_checklist=WorkChecklistRead(items=[], filled_count=0, total_count=0),
        records=records,
    )


def _full_day() -> tuple[SourceRecord, ...]:
    return (
        _record("drug-a", MEDICATION, [("標題", "Drug-A"), ("類別", "PRN")]),
        _record("drug-b", MEDICATION, [("標題", "Drug-B")]),
        _record("drug-old", MEDICATION, [("標題", "Drug-Old")], day=PREVIOUS_DAY),
        _record("note-1", NURSING, [("內容", "服藥後主訴頭暈，已通知醫師")]),
        _record("vital-1", VITAL, [("體溫", "37.2")]),
        _record("lab-1", LAB, [("項目", "白血球"), ("值", "11.0")]),
    )


def test_rule_is_event_cycle_with_prompt_identity() -> None:
    assert (RULE.code, RULE.cycle, RULE.prompt_name, RULE.prompt_version) == (
        "R07",
        AuditCycle.EVENT,
        "r07_medication_followup",
        1,
    )
    assert RULE.output_schema is R07Output


def test_check_availability_is_data_unavailable_with_reason() -> None:
    availability = RULE.check_availability(_ctx(_full_day()))

    assert availability.state == AvailabilityState.DATA_UNAVAILABLE
    assert availability.reason is not None
    assert availability.reason.startswith("院方尚未提供所需資料")
    assert "PRN" in availability.reason


def test_build_input_cites_same_day_medications_nursing_and_auxiliary() -> None:
    audit_input = RULE.build_input(_ctx(_full_day()))

    cited = [record.record_id for record in audit_input.records]
    assert cited == ["drug-a", "drug-b", "note-1", "vital-1", "lab-1"]
    assert audit_input.variables["drug_names_block"] == "- Drug-A\n- Drug-B"
    assert audit_input.variables["medication_status"] == "本日有用藥紀錄（2 筆）"
    assert audit_input.variables["nursing_status"] == "本日有護理紀錄（1 筆）"
    assert audit_input.variables["vital_status"] == "本日有生命徵象（1 筆）"
    assert audit_input.variables["lab_status"] == "本日有檢驗結果（1 筆）"
    assert audit_input.variables["response_elements_block"] == "通知醫師、處理、通報、紀錄"


def test_build_input_without_data_reports_missing_items() -> None:
    audit_input = RULE.build_input(_ctx(()))

    assert audit_input.records == ()
    assert audit_input.variables["drug_names_block"] == "本日沒有用藥紀錄"
    assert audit_input.variables["medication_status"] == "本日沒有用藥紀錄"
    assert audit_input.variables["vital_status"] == "本日未見生命徵象"


def test_prompt_renders_with_build_input_variables() -> None:
    audit_input = RULE.build_input(_ctx(_full_day()))
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    assert "- Drug-A\n- Drug-B" in text
    assert 'source="medication_order" id="drug-a"' in text
    assert "尚待確認" in text  # 追蹤時限未定，prompt 不寫死
    assert "通知醫師、處理、通報、紀錄" in text


def test_prompt_renders_with_fabricated_empty_input() -> None:
    audit_input = RULE.build_input(_ctx(()))
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    assert "本日沒有用藥紀錄" in text
    assert "（本次沒有可引用的紀錄）" in text


def _output(medications: list[dict[str, Any]], findings: list[dict[str, Any]]) -> R07Output:
    return R07Output.model_validate(
        {"verdict": "WARNING", "summary": "x", "findings": findings, "medications": medications}
    )


def _input_with_drugs() -> AuditInput:
    return RULE.build_input(_ctx(_full_day()))


def test_valid_output_is_accepted_and_keeps_medication_details() -> None:
    parsed = _output(
        medications=[{"drug": "Drug-A", "effect_described": True, "side_effect_described": False}],
        findings=[
            {"item": "Drug-A", "verdict": "WARNING", "message": "Drug-A 未見副作用追蹤紀錄"},
        ],
    )
    assert isinstance(parsed, RuleOutput)

    RULE.validate_output(parsed, _input_with_drugs())
    assert parsed.model_dump(exclude=set(RuleOutput.model_fields)) == {
        "medications": [
            {"drug": "Drug-A", "effect_described": True, "side_effect_described": False}
        ]
    }


def test_response_item_is_allowed_in_findings() -> None:
    parsed = _output(
        medications=[],
        findings=[{"item": RESPONSE_ITEM, "verdict": "WARNING", "message": "未見通報紀錄"}],
    )

    RULE.validate_output(parsed, _input_with_drugs())


def test_drug_outside_todays_medications_is_rejected() -> None:
    parsed = _output(
        medications=[{"drug": "Drug-Old", "effect_described": True, "side_effect_described": True}],
        findings=[],
    )

    with pytest.raises(LLMOutputError):
        RULE.validate_output(parsed, _input_with_drugs())


def test_finding_item_outside_allowed_names_is_rejected() -> None:
    parsed = _output(
        medications=[],
        findings=[{"item": "不存在的項目", "verdict": "WARNING", "message": "x"}],
    )

    with pytest.raises(LLMOutputError):
        RULE.validate_output(parsed, _input_with_drugs())


async def test_service_run_is_data_unavailable_without_calling_llm(
    session: AsyncSession,
    audit_hospital_data_source: HospitalDataSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[LLMRequest] = []

    async def fake(*args: Any, **kwargs: Any) -> Any:
        calls.append(args[1])
        raise AssertionError("R07 不應呼叫 LLM")

    monkeypatch.setattr(gateway, "complete_structured", fake)
    service = AuditService(audit_hospital_data_source)

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R07")

    assert result.status == AuditRunStatus.DATA_UNAVAILABLE
    assert result.status_reason is not None
    assert result.status_reason.startswith("院方尚未提供所需資料")
    assert calls == []
