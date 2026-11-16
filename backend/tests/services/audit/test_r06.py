"""R06 逐筆追蹤測試（虛構資料，不呼叫 LLM）；依指定修改範圍集中情境與反例，超過 300 行。"""

import re
from dataclasses import replace
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.enums import AvailabilityState, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.llm_structured import LlmEvidence, LlmFinding, RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.evidence import verify_output
from app.services.audit.records import SourceField, SourceRecord, render_records_block
from app.services.audit.rules import r06_consultation
from app.services.audit.rules.base import AuditInput, LabelsFindings
from app.services.audit.rules.r06_consultation import (
    ConsultationMatch,
    ConsultationStatus,
    R06Consultation,
    R06Output,
)
from app.services.audit.views import run_finding_labels
from app.services.llm.prompt_loader import PROMPTS_DIR, render_prompt

_DAY = date(2032, 2, 1)
_PREVIOUS = _DAY - timedelta(days=1)
_ITEM = f"{_PREVIOUS} 胸腔內科"


def _record(record_id: str, day: date, category: str = "胸腔內科(V:醫師甲)") -> SourceRecord:
    is_note = record_id.startswith("note")
    fields = (SourceField("類別", category),)
    if is_note:
        fields += (SourceField("內容", f"{_PREVIOUS} 胸腔內科醫師甲會診，建議追蹤。"),)
    return SourceRecord(
        record_id=record_id,
        source=(
            RawRecordCategory.NURSING_PROGRESS_NOTE if is_note else RawRecordCategory.CONSULTATION
        ),
        business_date=day,
        time_text=f"{day:%Y/%m/%d} 16:22",
        recorded_at=None,
        fields=fields,
    )


def _ctx(records: tuple[SourceRecord, ...], earliest: date = _PREVIOUS) -> AuditContext:
    return AuditContext(
        patient_key="FAKE-PATIENT",
        ward_code="FAKE-WARD",
        bed_code="01",
        business_date=_DAY,
        patient_dates=(_DAY, earliest),
        admitted_at=None,
        admitted_at_text=None,
        work_checklist=WorkChecklistRead(items=[], filled_count=0, total_count=0),
        records=records,
    )


def _input(earliest: date = _PREVIOUS) -> AuditInput:
    return R06Consultation(1).build_input(
        _ctx((_record("consult-1", _PREVIOUS), _record("note-1", _DAY, "會診")), earliest)
    )


def _output(status: ConsultationStatus = "NOT_FOUND", complete: bool = True) -> R06Output:
    verdict = "PASS" if status != "NOT_FOUND" else "WARNING" if complete else "NEEDS_REVIEW"
    return R06Output.model_validate(
        {
            "verdict": verdict,
            "summary": "請確認會診追蹤狀況",
            "consultations": [{"record_id": "consult-1", "item": _ITEM, "status": status}],
            "findings": [
                {
                    "item": _ITEM,
                    "verdict": verdict,
                    "message": "已見對應的護理紀錄" if status == "MATCHED" else "請確認追蹤狀況",
                    "evidence": [
                        {
                            "record_id": "note-1" if status == "MATCHED" else "consult-1",
                            "excerpt": "胸腔內科",
                        }
                    ],
                }
            ],
        }
    )


def test_identity_and_optional_interface() -> None:
    rule = R06Consultation(1)
    assert (rule.code, rule.prompt_name, rule.prompt_version, rule.cycle.value) == (
        "R06",
        "r06_consultation",
        3,
        "event",
    )
    assert isinstance(rule, LabelsFindings)
    assert not hasattr(rule, "status_notes")


def test_only_grace_consultation_is_available_and_passes() -> None:
    rule = R06Consultation(1)
    ctx = _ctx((_record("consult-1", _DAY),))
    audit_input = rule.build_input(ctx)
    output = _output("IN_GRACE")
    output.consultations[0].item = output.findings[0].item = f"{_DAY} 胸腔內科"

    rule.validate_output(output, audit_input)

    assert rule.check_availability(ctx).state == AvailabilityState.AVAILABLE
    assert audit_input.records == ctx.records
    assert f"到期日：{_DAY + timedelta(days=1)}" in audit_input.variables["consult_block"]
    assert "期限狀態：寬限期中" in audit_input.variables["consult_block"]
    assert output.verdict == "PASS"


@pytest.mark.parametrize(
    "status,complete",
    [("MATCHED", True), ("MATCHED", False), ("NOT_FOUND", True), ("NOT_FOUND", False)],
)
def test_due_consultation_valid_outcomes(status: ConsultationStatus, complete: bool) -> None:
    audit_input = _input(_PREVIOUS if complete else _DAY)
    output = _output(status, complete)

    R06Consultation(1).validate_output(output, audit_input)
    verified = verify_output(output, {record.record_id: record for record in audit_input.records})

    assert verified.verdict.value == output.verdict
    assert len(verified.findings[0].evidence) == 1
    assert verified.findings[0].evidence[0].source == (
        RawRecordCategory.NURSING_PROGRESS_NOTE
        if status == "MATCHED"
        else RawRecordCategory.CONSULTATION
    )


def test_mixed_due_and_grace_use_per_consultation_data_status() -> None:
    rule = R06Consultation(1)
    audit_input = rule.build_input(
        _ctx((_record("consult-1", _PREVIOUS), _record("consult-2", _DAY)), _DAY)
    )
    output = _output(complete=False)
    item = f"{_DAY} 胸腔內科"
    output.consultations.append(
        ConsultationMatch(record_id="consult-2", item=item, status="IN_GRACE")
    )
    output.findings.append(
        LlmFinding(
            item=item,
            verdict="PASS",
            message="寬限期中",
            evidence=[LlmEvidence(record_id="consult-2", excerpt="胸腔內科")],
        )
    )

    rule.validate_output(output, audit_input)

    facts = audit_input.facts["consultation_facts"]
    assert isinstance(facts, list)
    assert [fact["data_complete"] for fact in facts] == [False, True]
    assert "尚未到齊" in audit_input.variables["consult_block"]
    assert "已到齊" in audit_input.variables["consult_block"]
    assert output.verdict == "NEEDS_REVIEW"


@pytest.mark.parametrize("days", [0, 1, 2])
def test_window_filters_dates_sources_and_categories(days: int) -> None:
    start = _DAY - timedelta(days=days)
    ctx = _ctx(
        (
            _record("consult-before", start - timedelta(days=1)),
            _record("consult-start", start),
            _record("consult-end", _DAY),
            _record("consult-future", _DAY + timedelta(days=1)),
            _record("note-before", start - timedelta(days=1), "會診"),
            _record("note-start", start, "會診"),
            _record("note-end", _DAY, "營養照會建議"),
            _record("note-other", _DAY, "一般護理"),
            _record("note-future", _DAY + timedelta(days=1), "會診"),
        ),
        start,
    )

    audit_input = R06Consultation(days).build_input(ctx)

    assert [record.record_id for record in audit_input.records] == [
        "consult-start",
        "consult-end",
        "note-start",
        "note-end",
    ]
    assert audit_input.variables["window_start"] == str(start)
    facts = audit_input.facts["consultation_facts"]
    assert isinstance(facts, list)
    assert [fact["is_due"] for fact in facts] == [True, days == 0]
    assert [fact["deadline"] for fact in facts] == [str(_DAY), str(_DAY + timedelta(days=days))]


def test_no_consultations_in_window_is_not_applicable() -> None:
    ctx = _ctx(
        (
            _record("consult-old", _PREVIOUS - timedelta(days=1)),
            _record("consult-future", _DAY + timedelta(days=1)),
            _record("note-1", _DAY, "會診"),
        )
    )
    assert R06Consultation(1).check_availability(ctx).state == AvailabilityState.NOT_APPLICABLE


def test_days_from_settings_and_constructor_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        r06_consultation, "get_settings", lambda: SimpleNamespace(AUDIT_CONSULT_FOLLOWUP_DAYS=2)
    )
    ctx = _ctx((_record("consult-1", _DAY - timedelta(days=2)),))
    assert R06Consultation().build_input(ctx).variables["window_start"] == str(
        _DAY - timedelta(days=2)
    )
    assert R06Consultation(0).check_availability(ctx).state == AvailabilityState.NOT_APPLICABLE


@pytest.mark.parametrize(
    "category,expected",
    [
        ("胸腔內科(V:醫師甲)", "胸腔內科"),
        ("胸腔內科（V:醫師甲）", "胸腔內科"),
        ("(醫師甲)", "院方未提供科別"),
        ("", "院方未提供科別"),
    ],
)
def test_item_strips_physician_annotation(category: str, expected: str) -> None:
    audit_input = R06Consultation(1).build_input(_ctx((_record("consult-1", _PREVIOUS, category),)))
    assert f"item={_PREVIOUS} {expected}｜" in audit_input.variables["consult_block"]


def test_same_day_same_department_remains_one_finding_per_record() -> None:
    audit_input = R06Consultation(1).build_input(
        _ctx((_record("consult-1", _PREVIOUS), _record("consult-2", _PREVIOUS)))
    )
    output = _output()
    output.consultations.append(
        output.consultations[0].model_copy(update={"record_id": "consult-2"})
    )
    output.findings.append(output.findings[0].model_copy(deep=True))
    output.findings[1].evidence[0].record_id = "consult-2"
    R06Consultation(1).validate_output(output, audit_input)


@pytest.mark.parametrize("mutation", ["missing", "unknown", "duplicate", "note_id"])
def test_rejects_invalid_consultation_coverage(mutation: str) -> None:
    output = _output()
    if mutation == "missing":
        output.consultations.clear()
    elif mutation == "duplicate":
        output.consultations.append(output.consultations[0])
    else:
        output.consultations[0].record_id = "note-1" if mutation == "note_id" else "unknown"
    with pytest.raises(LLMOutputError, match="會診清單"):
        R06Consultation(1).validate_output(output, _input())


@pytest.mark.parametrize("days,status", [(1, "IN_GRACE"), (2, "NOT_FOUND"), (0, "IN_GRACE")])
def test_rejects_status_inconsistent_with_deadline(days: int, status: ConsultationStatus) -> None:
    ctx = _ctx((_record("consult-1", _DAY if days == 0 else _PREVIOUS),))
    with pytest.raises(LLMOutputError, match="追蹤期限"):
        R06Consultation(days).validate_output(
            _output(status), R06Consultation(days).build_input(ctx)
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "wrong_item",
        "wrong_match_item",
        "warning_for_matched",
        "pass_for_missing",
        "review_for_complete",
    ],
)
def test_rejects_findings_inconsistent_with_status(mutation: str) -> None:
    output = _output()
    if mutation == "missing":
        output.findings.clear()
    elif mutation == "extra":
        output.findings.append(output.findings[0])
    else:
        _mutate_finding(output, mutation)
    with pytest.raises(LLMOutputError, match="發現與會診"):
        R06Consultation(1).validate_output(output, _input())


def _mutate_finding(output: R06Output, mutation: str) -> None:
    if mutation == "wrong_item":
        output.findings[0].item = "其他項目"
    elif mutation == "wrong_match_item":
        output.consultations[0].item = "其他項目"
    elif mutation == "warning_for_matched":
        output.consultations[0].status = "MATCHED"
    else:
        output.findings[0].verdict = "PASS" if mutation == "pass_for_missing" else "NEEDS_REVIEW"


def test_rejects_incomplete_data_warning_per_consultation() -> None:
    with pytest.raises(LLMOutputError, match="尚未到齊"):
        R06Consultation(1).validate_output(_output(), _input(_DAY))


@pytest.mark.parametrize(
    "status,verdict", [("NOT_FOUND", "PASS"), ("MATCHED", "WARNING"), ("NOT_FOUND", "NEEDS_REVIEW")]
)
def test_rejects_inconsistent_overall_verdict(status: ConsultationStatus, verdict: str) -> None:
    output = _output(status)
    output = R06Output.model_validate({**output.model_dump(), "verdict": verdict})
    with pytest.raises(LLMOutputError, match="整體判定"):
        R06Consultation(1).validate_output(output, _input())


@pytest.mark.parametrize("word", ["寫錯", "漏寫", "違規", "忘記"])
@pytest.mark.parametrize("target", ["summary", "message"])
def test_rejects_accusatory_wording(word: str, target: str) -> None:
    output = _output()
    if target == "summary":
        output.summary = f"護理師{word}"
    else:
        output.findings[0].message = f"護理師{word}"
    with pytest.raises(LLMOutputError, match="提醒原則"):
        R06Consultation(1).validate_output(output, _input())


@pytest.mark.parametrize(
    "status,evidence_id",
    [
        ("MATCHED", "consult-1"),
        ("NOT_FOUND", "note-1"),
        ("MATCHED", "unknown"),
        ("NOT_FOUND", None),
    ],
)
def test_rejects_wrong_or_missing_evidence(
    status: ConsultationStatus, evidence_id: str | None
) -> None:
    output = _output(status)
    output.findings[0].evidence = (
        [] if evidence_id is None else [LlmEvidence(record_id=evidence_id, excerpt="胸腔內科")]
    )
    with pytest.raises(LLMOutputError, match="依據"):
        R06Consultation(1).validate_output(output, _input())


def test_matched_note_before_consultation_is_rejected() -> None:
    ctx = _ctx((_record("consult-1", _DAY), _record("note-1", _PREVIOUS, "會診")))
    output = _output("MATCHED")
    output.consultations[0].item = output.findings[0].item = f"{_DAY} 胸腔內科"
    with pytest.raises(LLMOutputError, match="依據"):
        R06Consultation(1).validate_output(output, R06Consultation(1).build_input(ctx))


def test_non_r06_output_is_rejected() -> None:
    with pytest.raises(LLMOutputError, match="會診清單"):
        R06Consultation(1).validate_output(RuleOutput(verdict="PASS", summary="請確認"), _input())


def test_schema_rejects_unknown_status() -> None:
    payload = _output().model_dump()
    payload["consultations"][0]["status"] = "UNKNOWN"
    with pytest.raises(ValidationError):
        R06Output.model_validate(payload)


@pytest.mark.parametrize(
    "details",
    [
        None,
        {},
        {"consultations": None},
        {"consultations": []},
        {"consultations": [{"record_id": "consult-1", "matched": False}]},
    ],
)
def test_finding_labels_empty_without_current_details(details: dict[str, object] | None) -> None:
    assert run_finding_labels(R06Consultation(1), details) == {}


def test_finding_labels_only_override_grace() -> None:
    details = {
        "consultations": [
            {"record_id": "consult-1", "item": "項目甲", "status": "IN_GRACE"},
            {"record_id": "consult-2", "item": "項目乙", "status": "MATCHED"},
            {"record_id": "consult-3", "item": "項目丙", "status": "NOT_FOUND"},
        ]
    }
    assert run_finding_labels(R06Consultation(1), details) == {"項目甲": "寬限期中"}


@pytest.mark.parametrize("day", [date(2031, 1, 1), date(2033, 12, 31)])
def test_prompt_dates_all_come_from_input(day: date) -> None:
    rule = R06Consultation(1)
    ctx = replace(_ctx((_record("consult-1", day),)), business_date=day, patient_dates=(day,))
    audit_input = rule.build_input(ctx)
    text = render_prompt(
        rule.prompt_name,
        rule.prompt_version,
        {**audit_input.variables, "records_block": render_records_block(audit_input.records)},
    )
    template = (PROMPTS_DIR / "r06_consultation/v3.j2").read_text()

    assert not re.search(r"\d{4}[-/]\d{2}[-/]\d{2}", template)
    assert set(re.findall(r"\d{4}[-/]\d{2}[-/]\d{2}", text)) <= {
        str(day - timedelta(days=1)),
        str(day),
        str(day + timedelta(days=1)),
        day.strftime("%Y/%m/%d"),
    }
    assert "寬限期中不是缺漏" in text
    assert "次日記前一日" in text
    assert "內文的日期時間" in text
    assert "營養照會建議" in text
    assert "{{" not in text
    assert 'id="consult-1"' in text


@pytest.mark.parametrize("verdict", ["WARNING", "NEEDS_REVIEW"])
def test_grace_finding_must_be_pass(verdict: str) -> None:
    ctx = _ctx((_record("consult-1", _DAY),))
    output = _output("IN_GRACE")
    output.consultations[0].item = output.findings[0].item = f"{_DAY} 胸腔內科"
    output.findings[0] = LlmFinding.model_validate(
        {**output.findings[0].model_dump(), "verdict": verdict}
    )
    with pytest.raises(LLMOutputError, match="發現與會診"):
        R06Consultation(1).validate_output(output, R06Consultation(1).build_input(ctx))


def test_matched_in_grace_is_pass_and_uses_default_label() -> None:
    ctx = _ctx((_record("consult-1", _DAY), _record("note-1", _DAY, "會診")))
    output = _output("MATCHED")
    output.consultations[0].item = output.findings[0].item = f"{_DAY} 胸腔內科"

    R06Consultation(1).validate_output(output, R06Consultation(1).build_input(ctx))

    assert run_finding_labels(R06Consultation(1), output.model_dump()) == {}
    assert output.verdict == "PASS"


def test_two_days_includes_middle_day_in_grace() -> None:
    ctx = _ctx(
        (
            _record("consult-1", _DAY - timedelta(days=2)),
            _record("consult-2", _PREVIOUS),
            _record("consult-3", _DAY),
        ),
        _DAY - timedelta(days=2),
    )
    audit_input = R06Consultation(2).build_input(ctx)
    facts = audit_input.facts["consultation_facts"]

    assert isinstance(facts, list)
    assert [fact["is_due"] for fact in facts] == [True, False, False]
    assert [fact["deadline"] for fact in facts] == [
        str(_DAY),
        str(_DAY + timedelta(days=1)),
        str(_DAY + timedelta(days=2)),
    ]
