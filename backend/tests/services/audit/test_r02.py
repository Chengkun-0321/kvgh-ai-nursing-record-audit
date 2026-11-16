"""R02 紀錄複製／時效性：適用條件、回溯窗、類別對齊、相似度參考值、輸出驗證與 prompt 渲染。

全部使用虛構紀錄直接組成 AuditContext，不讀 data/，不呼叫 LLM。
"""

from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.enums import AuditCycle, AvailabilityState, RawRecordCategory
from app.core.exceptions import LLMOutputError
from app.schemas.hospital_data.patients import WorkChecklistRead
from app.schemas.llm_structured import RuleOutput
from app.services.audit.context import AuditContext
from app.services.audit.records import SourceField, SourceRecord, render_records_block
from app.services.audit.rules import r02_copy_paste
from app.services.audit.rules.base import AuditInput
from app.services.audit.rules.r02_comparison import similarity, window_start
from app.services.audit.rules.r02_copy_paste import R02CopyPaste, R02Output
from app.services.llm.prompt_loader import render_prompt

RULE = R02CopyPaste()
TODAY = date(2026, 1, 3)
NOTE = RawRecordCategory.NURSING_PROGRESS_NOTE.value
VITAL = RawRecordCategory.VITAL_SIGN.value
LAB = RawRecordCategory.LAB_RESULT.value
ASSESSMENT = RawRecordCategory.DAILY_PHYSICAL_ASSESSMENT.value


def _set_lookback(monkeypatch: pytest.MonkeyPatch, days: int) -> None:
    fake = SimpleNamespace(AUDIT_COPY_LOOKBACK_DAYS=days)
    monkeypatch.setattr(r02_copy_paste, "get_settings", lambda: fake)


def _rec(rid: str, source: str, day: date, fields: list[tuple[str, str]]) -> SourceRecord:
    return SourceRecord(
        record_id=rid,
        source=source,
        business_date=day,
        time_text=day.isoformat(),
        recorded_at=None,
        fields=tuple(SourceField(label, value) for label, value in fields),
    )


def _note(rid: str, day: date, tag: str, text: str) -> SourceRecord:
    return _rec(rid, NOTE, day, [("類別", tag), ("內容", text)])


def _ctx(records: list[SourceRecord], today: date = TODAY) -> AuditContext:
    return AuditContext(
        patient_key="虛構病人",
        ward_code="W99",
        bed_code="W99-001",
        business_date=today,
        patient_dates=tuple(sorted({r.business_date for r in records})),
        admitted_at=None,
        admitted_at_text=None,
        work_checklist=WorkChecklistRead(items=[], filled_count=0, total_count=0),
        records=tuple(records),
    )


def _output(payload: dict[str, Any]) -> R02Output:
    return R02Output.model_validate(payload)


def test_rule_identity_is_daily_with_prompt_identity() -> None:
    assert (RULE.code, RULE.cycle, RULE.prompt_name, RULE.prompt_version) == (
        "R02",
        AuditCycle.DAILY,
        "r02_copy_paste",
        1,
    )


def test_not_applicable_without_today_notes() -> None:
    ctx = _ctx([_note("n-1", date(2026, 1, 2), "交班", "前一日內容")])

    availability = RULE.check_availability(ctx)

    assert availability.state == AvailabilityState.NOT_APPLICABLE


def test_available_with_only_today_notes() -> None:
    ctx = _ctx([_note("n-1", TODAY, "交班", "當日內容")])

    assert RULE.check_availability(ctx).state == AvailabilityState.AVAILABLE


def test_window_includes_today_and_excludes_days_before_it(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_lookback(monkeypatch, 2)
    records = [
        _note("old", date(2025, 12, 31), "交班", "太早"),
        _note("prev", date(2026, 1, 2), "交班", "前一日"),
        _note("today", TODAY, "交班", "當日"),
    ]

    audit_input = RULE.build_input(_ctx(records))

    ids = [record.record_id for record in audit_input.records]
    assert ids == ["prev", "today"]
    assert window_start(TODAY, 2) == date(2026, 1, 2)


def test_similar_notes_are_compared_and_reported_as_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_lookback(monkeypatch, 5)
    body = "病人安靜，進食良好，傷口乾燥無滲出，持續觀察。"
    records = [
        _note("prev", date(2026, 1, 2), "交班", body),
        _note("today", TODAY, "交班", body),
    ]

    audit_input = RULE.build_input(_ctx(records))

    assert audit_input.variables["comparison_status"] == "有前幾日紀錄可比對"
    block = audit_input.variables["category_alignment_block"]
    assert "類別「交班」" in block
    assert "最近前日 2026-01-02" in block
    assert "程式相似度參考值 1.00" in block


def test_no_prior_records_are_stated_to_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_lookback(monkeypatch, 5)

    audit_input = RULE.build_input(_ctx([_note("today", TODAY, "交班", "當日")]))

    assert "沒有前幾日紀錄可比對" in audit_input.variables["comparison_status"]
    assert "無法比對" in audit_input.variables["category_alignment_block"]


def test_prior_is_nearest_day_with_same_category(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_lookback(monkeypatch, 5)
    records = [
        _note("d1", date(2026, 1, 1), "衛教指導", "衛教甲"),
        _note("d2", date(2026, 1, 2), "交班", "交班內容"),
        _note("today", TODAY, "衛教指導", "衛教甲"),
    ]

    audit_input = RULE.build_input(_ctx(records))

    block = audit_input.variables["category_alignment_block"]
    assert "最近前日 2026-01-01" in block


def test_similarity_normalizes_line_endings_and_noise_characters() -> None:
    assert similarity("第一行\r\n第二行", "第一行\n第二行\U000e01b5") == 1.0
    assert similarity("", "內容") is None


def test_similarity_drops_when_content_changes() -> None:
    score = similarity("病人安靜，進食良好。", "病人躁動不安，拒絕進食，需要約束。")

    assert score is not None
    assert score < 0.8


def test_vitals_labs_and_tubes_are_included_only_in_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_lookback(monkeypatch, 2)
    records = [
        _note("today", TODAY, "交班", "當日"),
        _rec("vital-today", VITAL, TODAY, [("體溫", "37.9℃"), ("脈搏", "110")]),
        _rec("vital-old", VITAL, date(2025, 12, 31), [("脈搏", "70")]),
        _rec("lab-normal", LAB, TODAY, [("Na", "140")]),
        replace(
            _rec("lab-abnormal", LAB, TODAY, []),
            fields=(SourceField("WBC", "12.0", "院方標記：偏高"), SourceField("Na", "140")),
        ),
        _rec(
            "assess-today",
            ASSESSMENT,
            TODAY,
            [("身評時間", "2026-01-03 08:00"), ("管路", "Foley 留置"), ("呼吸音", "清")],
        ),
        _rec("assess-no-tube", ASSESSMENT, TODAY, [("呼吸音", "清")]),
    ]

    audit_input = RULE.build_input(_ctx(records))

    ids = [record.record_id for record in audit_input.records]
    # 檢驗只送院方標記為異常的項目；沒有異常項目的檢驗紀錄不送
    assert ids == ["today", "vital-today", "lab-abnormal", "assess-today"]
    lab_record = audit_input.records[2]
    assert [field.label for field in lab_record.fields] == ["WBC"]
    tube_record = audit_input.records[-1]
    assert [field.label for field in tube_record.fields] == ["管路"]
    assert tube_record.time_text == "2026-01-03"


def test_prompt_renders_with_build_input_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_lookback(monkeypatch, 5)
    audit_input = RULE.build_input(
        _ctx(
            [
                _note("prev", date(2026, 1, 2), "交班", "前一日交班"),
                _note("today", TODAY, "交班", "當日交班"),
                _rec("vital-today", VITAL, TODAY, [("脈搏", "110")]),
            ]
        )
    )
    variables = {
        **audit_input.variables,
        "records_block": render_records_block(audit_input.records),
    }

    text = render_prompt(RULE.prompt_name, RULE.prompt_version, variables)

    assert "回溯期間：2025-12-30 至 2026-01-03（含當日）" in text
    assert 'source="nursing_progress_note"' in text
    assert "複製貼上" in text  # 禁用措辭只出現在「不得使用」的指示中
    assert "{{" not in text


def test_output_category_outside_input_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_lookback(monkeypatch, 5)
    audit_input = RULE.build_input(_ctx([_note("today", TODAY, "交班", "當日")]))
    output = _output(
        {
            "verdict": "PASS",
            "summary": "x",
            "category_judgements": [{"category": "不存在的類別", "judgement": "無法判斷"}],
        }
    )

    with pytest.raises(LLMOutputError):
        RULE.validate_output(output, audit_input)


def test_finding_item_outside_input_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_lookback(monkeypatch, 5)
    audit_input = RULE.build_input(_ctx([_note("today", TODAY, "交班", "當日")]))
    output = _output(
        {
            "verdict": "WARNING",
            "summary": "x",
            "findings": [{"item": "醫囑", "verdict": "WARNING", "message": "x"}],
        }
    )

    with pytest.raises(LLMOutputError):
        RULE.validate_output(output, audit_input)


def test_copy_judgement_without_prior_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_lookback(monkeypatch, 5)
    audit_input = RULE.build_input(_ctx([_note("today", TODAY, "交班", "當日")]))
    output = _output(
        {
            "verdict": "WARNING",
            "summary": "x",
            "category_judgements": [{"category": "交班", "judgement": "幾乎相同"}],
        }
    )

    with pytest.raises(LLMOutputError):
        RULE.validate_output(output, audit_input)


def test_valid_output_passes_and_keeps_category_judgements(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_lookback(monkeypatch, 5)
    records = [
        _note("prev", date(2026, 1, 2), "交班", "前一日交班"),
        _note("today", TODAY, "交班", "前一日交班"),
        _rec("vital-today", VITAL, TODAY, [("脈搏", "110")]),
    ]
    audit_input: AuditInput = RULE.build_input(_ctx(records))
    output = _output(
        {
            "verdict": "WARNING",
            "summary": "x",
            "findings": [
                {
                    "item": "交班",
                    "verdict": "WARNING",
                    "message": "交班與前一日幾乎相同，請確認",
                    "evidence": [{"record_id": "today", "excerpt": "前一日交班"}],
                },
            ],
            "category_judgements": [{"category": "交班", "judgement": "幾乎相同"}],
        }
    )

    RULE.validate_output(output, audit_input)

    assert output.model_dump(exclude=set(RuleOutput.model_fields)) == {
        "category_judgements": [{"category": "交班", "judgement": "幾乎相同"}]
    }
