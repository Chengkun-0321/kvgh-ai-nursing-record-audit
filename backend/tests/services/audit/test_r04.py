"""R04 每日身評異常追蹤：可執行判斷、輸入整理、專屬輸出驗證、prompt 渲染與 Evidence 核對。

全部使用虛構紀錄直接組成 AuditContext，不讀取 data/，不呼叫 LLM。
"""

from datetime import date
from typing import Any

import pytest

from app.core.enums import AuditCycle, AvailabilityState, RawRecordCategory, Verdict
from app.core.exceptions import LLMOutputError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.evidence import verify_output
from app.services.audit.records import SourceField, SourceRecord, render_records_block
from app.services.audit.rules.base import AuditInput
from app.services.audit.rules.r04_assessment_followup import R04AssessmentFollowup
from app.services.audit.rules.r04_output import R04Output
from app.services.llm.prompt_loader import render_prompt

RULE = R04AssessmentFollowup()
DAY = date(2026, 1, 2)
OTHER_DAY = date(2026, 1, 1)
ASSESSMENT_ID = "assess-0102"
NURSING_ID = "nursing-0102"
# 虛構的私用區字元（U+E01B5），確認核對時原文字元不會被改寫
ODD_CHAR = "\U000e01b5"
LUNG_TEXT = "右肺下葉可聞及囉音"
TUBE_TEXT = f"導尿管留置中\r\n尿液澄清\t顏色正常{ODD_CHAR}"


def _record(
    record_id: str, source: RawRecordCategory, day: date, fields: list[tuple[str, str]]
) -> SourceRecord:
    return SourceRecord(
        record_id=record_id,
        source=source.value,
        business_date=day,
        time_text=f"{day.isoformat()} 08:00",
        recorded_at=None,
        fields=tuple(SourceField(label, value) for label, value in fields),
    )


def _assessment(day: date = DAY) -> SourceRecord:
    fields = [
        ("意識", "清醒"),
        ("呼吸音", LUNG_TEXT),
        ("管路", TUBE_TEXT),
        ("皮膚", "完整，無發紅"),
    ]
    return _record(ASSESSMENT_ID, RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT, day, fields)


def _nursing(record_id: str = NURSING_ID, day: date = DAY) -> SourceRecord:
    note = [("內容", "呼吸型態平穩，給予氧氣 2L/min，協助採取半臥位")]
    return _record(record_id, RawRecordCategory.NURSING_PROGRESS_NOTE, day, note)


def _ctx(records: list[SourceRecord], day: date = DAY) -> AuditContext:
    return AuditContext(
        patient_key="TEST-P1",
        ward_code="TEST-W",
        bed_code="01",
        business_date=day,
        patient_dates=(OTHER_DAY, DAY),
        admitted_at=None,
        admitted_at_text=None,
        work_checklist=WorkChecklistRead(items=[], filled_count=0, total_count=0),
        records=tuple(records),
    )


def _assessment_input() -> AuditInput:
    return RULE.build_input(_ctx([_assessment(), _nursing()]))


def _not_found_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "verdict": "WARNING",
        "summary": "呼吸音異常，當日護理紀錄未見相應描述，請確認",
        "flagged_items": [{"item": "呼吸音", "status": "NOT_FOUND", "reason": "原文為囉音"}],
        "findings": [
            {
                "item": "呼吸音",
                "verdict": "WARNING",
                "message": "身評呼吸音異常，當日護理紀錄未見相應描述，請確認",
                "evidence": [{"record_id": ASSESSMENT_ID, "excerpt": LUNG_TEXT}],
            }
        ],
    }
    payload.update(overrides)
    return payload


def _with_finding(**changes: Any) -> dict[str, Any]:
    payload = _not_found_payload()
    payload["findings"][0].update(changes)
    return payload


def test_rule_identity_is_daily_with_prompt_version() -> None:
    assert (RULE.code, RULE.prompt_name, RULE.prompt_version) == (
        "R04",
        "r04_assessment_followup",
        1,
    )
    assert RULE.cycle == AuditCycle.DAILY


def test_not_applicable_when_day_has_no_assessment() -> None:
    availability = RULE.check_availability(_ctx([_nursing()]))

    assert availability.state == AvailabilityState.NOT_APPLICABLE
    assert availability.reason == "當日沒有每日身體評估"


def test_not_applicable_ignores_assessment_from_other_day() -> None:
    ctx = _ctx([_assessment(OTHER_DAY)])

    assert RULE.check_availability(ctx).state == AvailabilityState.NOT_APPLICABLE


def test_available_when_day_has_assessment() -> None:
    assert RULE.check_availability(_ctx([_assessment()])).state == AvailabilityState.AVAILABLE


def test_build_input_uses_same_day_records_and_auxiliary_sources() -> None:
    other_day_note = _nursing("nursing-0101", OTHER_DAY)
    vital = _record("vital-0102", RawRecordCategory.VITAL_SIGN, DAY, [("體溫", "37.2")])
    medication = _record("med-0102", RawRecordCategory.MEDICATION_ORDER, DAY, [("藥名", "吸入劑")])
    ctx = _ctx([_assessment(), _nursing(), other_day_note, vital, medication])

    audit_input = RULE.build_input(ctx)

    assert [record.record_id for record in audit_input.records] == [
        ASSESSMENT_ID,
        NURSING_ID,
        "vital-0102",
        "med-0102",
    ]


def test_variables_list_assessment_names_and_flag_missing_nursing_notes() -> None:
    audit_input = RULE.build_input(_ctx([_assessment()]))

    assert audit_input.variables["assessment_items_block"] == "- 意識\n- 呼吸音\n- 管路\n- 皮膚"
    assert audit_input.variables["nursing_note_status"].startswith("當日沒有護理紀錄")
    assert "UNCERTAIN" in audit_input.variables["nursing_note_status"]


def test_nursing_status_counts_notes_when_present() -> None:
    status = _assessment_input().variables["nursing_note_status"]

    assert status.startswith("當日有 1 筆護理紀錄")


def test_prompt_renders_with_build_input_variables() -> None:
    audit_input = _assessment_input()
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    assert "- 呼吸音" in text
    assert 'source="daily_physical_assessment"' in text
    assert f'id="{NURSING_ID}"' in text
    assert "{{" not in text


def test_valid_not_found_output_passes_and_keeps_flagged_items_in_details() -> None:
    parsed = R04Output.model_validate(_not_found_payload())

    RULE.validate_output(parsed, _assessment_input())

    assert parsed.model_dump(mode="json", exclude=set(RuleOutput.model_fields)) == {
        "flagged_items": [{"item": "呼吸音", "status": "NOT_FOUND", "reason": "原文為囉音"}]
    }


def test_found_item_without_finding_is_accepted() -> None:
    payload = {
        "verdict": "PASS",
        "summary": "身評異常項目皆有相應紀錄",
        "flagged_items": [{"item": "呼吸音", "status": "FOUND", "reason": "有給氧與擺位描述"}],
        "findings": [],
    }

    RULE.validate_output(R04Output.model_validate(payload), _assessment_input())


@pytest.mark.parametrize(
    "payload",
    [
        # 項目不在身評欄位名稱內
        _not_found_payload(flagged_items=[{"item": "心跳", "status": "NOT_FOUND", "reason": "x"}]),
        # 同一項目重複列出
        _not_found_payload(
            flagged_items=[
                {"item": "呼吸音", "status": "NOT_FOUND", "reason": "x"},
                {"item": "呼吸音", "status": "NOT_FOUND", "reason": "x"},
            ]
        ),
        # NOT_FOUND 沒有 WARNING finding
        _not_found_payload(findings=[]),
        # UNCERTAIN 卻給 WARNING
        _not_found_payload(
            flagged_items=[{"item": "呼吸音", "status": "UNCERTAIN", "reason": "x"}]
        ),
        # FOUND 卻給 WARNING
        _not_found_payload(flagged_items=[{"item": "呼吸音", "status": "FOUND", "reason": "x"}]),
        # 未列為異常的項目出現 finding
        _not_found_payload(flagged_items=[]),
        # NOT_FOUND 的依據指向護理紀錄，而非身評
        _with_finding(evidence=[{"record_id": NURSING_ID, "excerpt": "給予氧氣"}]),
        # 用語指責護理師
        _with_finding(message="護理師漏寫呼吸音，請確認"),
    ],
)
def test_inconsistent_output_is_rejected(payload: dict[str, Any]) -> None:
    with pytest.raises(LLMOutputError):
        RULE.validate_output(R04Output.model_validate(payload), _assessment_input())


def test_verify_keeps_excerpt_across_whitespace_and_odd_characters() -> None:
    records = {record.record_id: record for record in _assessment_input().records}
    excerpt = f"導尿管留置中 尿液澄清 顏色正常{ODD_CHAR}"
    payload = _not_found_payload(
        flagged_items=[{"item": "管路", "status": "NOT_FOUND", "reason": "x"}],
        findings=[
            {
                "item": "管路",
                "verdict": "WARNING",
                "message": "身評管路異常，當日護理紀錄未見相應描述，請確認",
                "evidence": [{"record_id": ASSESSMENT_ID, "excerpt": excerpt}],
            }
        ],
    )

    verified = verify_output(R04Output.model_validate(payload), records)

    assert verified.verdict == Verdict.WARNING
    (finding,) = verified.findings
    assert finding.evidence[0].field == "管路"
    assert finding.evidence[0].record_id == ASSESSMENT_ID


@pytest.mark.parametrize("excerpt", [f"右肺下葉可聞及囉音{ODD_CHAR}X", "胸痛"])
def test_verify_drops_fabricated_or_altered_excerpt(excerpt: str) -> None:
    records = {record.record_id: record for record in _assessment_input().records}
    payload = _with_finding(evidence=[{"record_id": ASSESSMENT_ID, "excerpt": excerpt}])

    verified = verify_output(R04Output.model_validate(payload), records)

    assert verified.verdict == Verdict.NEEDS_REVIEW
    assert verified.findings[0].evidence == ()
