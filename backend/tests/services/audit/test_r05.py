"""R05 預留規則：不可執行判斷、輸入整理（虛構資料）、輸出驗證與 prompt 渲染。"""

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
from app.services.audit.rules.r05_transfer_summary import (
    INCOMING_SUMMARY,
    OUTGOING_SUMMARY,
    R05Output,
    R05TransferSummary,
)
from app.services.audit.service import AuditService
from app.services.hospital_data.source import HospitalDataSource
from app.services.llm import gateway
from app.services.llm.prompt_loader import render_prompt
from tests.hospital_data_samples import AUDIT_P3_KEY

RULE = R05TransferSummary()
DAY = date(2026, 1, 2)
PREVIOUS_DAY = date(2026, 1, 1)
SELECTED_DAY = date(2026, 1, 2)
TRANSFER = RawRecordCategory.BED_TRANSFER.value
NURSING = RawRecordCategory.NURSING_PROGRESS_NOTE.value
DAILY = RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT.value


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
        patient_key="TEST-R05",
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
        _record("transfer-1", TRANSFER, [("轉床", "病房內換床")]),
        _record(
            "note-out",
            NURSING,
            [("類別", OUTGOING_SUMMARY), ("內容", "因肺炎住院，目前病況穩定")],
        ),
        _record("note-in", NURSING, [("類別", INCOMING_SUMMARY), ("內容", "意識清楚")]),
        _record("note-plain", NURSING, [("類別", "一般護理"), ("內容", "無特殊")]),
        _record(
            "daily-1",
            DAILY,
            [("呼吸音", "正常"), ("管路：鼻胃管", "留置中")],
        ),
        _record("daily-2", DAILY, [("呼吸音", "正常")]),
        _record("transfer-old", TRANSFER, [("轉床", "舊紀錄")], day=PREVIOUS_DAY),
    )


def test_rule_is_event_cycle_with_prompt_identity() -> None:
    assert (RULE.code, RULE.cycle, RULE.prompt_name, RULE.prompt_version) == (
        "R05",
        AuditCycle.EVENT,
        "r05_transfer_summary",
        1,
    )
    assert RULE.output_schema is R05Output


def test_check_availability_is_data_unavailable_with_reason() -> None:
    availability = RULE.check_availability(_ctx(_full_day()))

    assert availability.state == AvailabilityState.DATA_UNAVAILABLE
    assert availability.reason is not None
    assert availability.reason.startswith("院方尚未提供所需資料")
    assert "轉出摘要" in availability.reason and "轉入摘要" in availability.reason


def test_build_input_cites_same_day_transfer_summaries_and_tubes() -> None:
    audit_input = RULE.build_input(_ctx(_full_day()))

    cited = [record.record_id for record in audit_input.records]
    assert cited == ["transfer-1", "note-out", "note-in", "daily-1"]
    assert audit_input.variables["transfer_status"] == "本日有轉床紀錄（1 筆）"
    assert audit_input.variables["outgoing_status"] == "有紀錄（1 筆）"
    assert audit_input.variables["incoming_status"] == "有紀錄（1 筆）"
    assert audit_input.variables["tube_block"] == f"- {DAY.isoformat()} 管路：鼻胃管：留置中"


def test_build_input_without_data_reports_missing_summaries() -> None:
    audit_input = RULE.build_input(_ctx(()))

    assert audit_input.records == ()
    assert audit_input.variables["transfer_status"] == "本日沒有轉床紀錄"
    assert audit_input.variables["outgoing_status"] == "未見紀錄或院方未提供"
    assert audit_input.variables["incoming_status"] == "未見紀錄或院方未提供"
    assert audit_input.variables["tube_block"] == "本日身評未見管路資料"


def test_required_elements_block_marks_conditional_items() -> None:
    audit_input = RULE.build_input(_ctx(()))

    block = audit_input.variables["required_elements_block"]
    assert "轉出摘要：住院期間重要檢查、治療結果、目前病況、管路、傷口（視病人狀況）" in block
    assert "轉入摘要：意識、呼吸、身體活動、管路、皮膚狀況、現存健康問題" in block


def test_prompt_renders_with_build_input_variables() -> None:
    audit_input = RULE.build_input(_ctx(_full_day()))
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    assert 'source="bed_transfer" id="transfer-1"' in text
    assert "鼻胃管" in text
    assert "轉出摘要：住院期間重要檢查" in text


def test_prompt_renders_with_fabricated_empty_input() -> None:
    audit_input = RULE.build_input(_ctx(()))
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    assert "本日沒有轉床紀錄" in text
    assert "（本次沒有可引用的紀錄）" in text


def _output(elements: list[dict[str, Any]], findings: list[dict[str, Any]]) -> R05Output:
    return R05Output.model_validate(
        {"verdict": "WARNING", "summary": "x", "findings": findings, "elements": elements}
    )


def test_valid_output_is_accepted_and_keeps_element_details() -> None:
    parsed = _output(
        elements=[{"summary_kind": "轉出摘要", "element": "管路", "mentioned": False}],
        findings=[
            {
                "item": "轉出摘要：管路",
                "verdict": "WARNING",
                "message": "轉出摘要未見管路相關描述，請確認",
            }
        ],
    )
    assert isinstance(parsed, RuleOutput)

    RULE.validate_output(parsed, AuditInput(variables={}))
    assert parsed.model_dump(exclude=set(RuleOutput.model_fields)) == {
        "elements": [{"summary_kind": "轉出摘要", "element": "管路", "mentioned": False}]
    }


def test_element_outside_summary_kind_is_rejected() -> None:
    parsed = _output(
        elements=[{"summary_kind": "轉出摘要", "element": "皮膚狀況", "mentioned": True}],
        findings=[],
    )

    with pytest.raises(LLMOutputError):
        RULE.validate_output(parsed, AuditInput(variables={}))


def test_finding_item_outside_allowed_names_is_rejected() -> None:
    parsed = _output(
        elements=[],
        findings=[{"item": "不存在的項目", "verdict": "WARNING", "message": "x"}],
    )

    with pytest.raises(LLMOutputError):
        RULE.validate_output(parsed, AuditInput(variables={}))


def test_summary_kind_as_missing_summary_item_is_accepted() -> None:
    parsed = _output(
        elements=[],
        findings=[{"item": INCOMING_SUMMARY, "verdict": "WARNING", "message": "未見轉入摘要"}],
    )

    RULE.validate_output(parsed, AuditInput(variables={}))


async def test_service_run_is_data_unavailable_without_calling_llm(
    session: AsyncSession,
    audit_hospital_data_source: HospitalDataSource,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[LLMRequest] = []

    async def fake(*args: Any, **kwargs: Any) -> Any:
        calls.append(args[1])
        raise AssertionError("R05 不應呼叫 LLM")

    monkeypatch.setattr(gateway, "complete_structured", fake)
    service = AuditService(audit_hospital_data_source)

    result = await service.run_rule(session, AUDIT_P3_KEY, SELECTED_DAY, "R05")

    assert result.status == AuditRunStatus.DATA_UNAVAILABLE
    assert result.status_reason is not None
    assert result.status_reason.startswith("院方尚未提供所需資料")
    assert calls == []
