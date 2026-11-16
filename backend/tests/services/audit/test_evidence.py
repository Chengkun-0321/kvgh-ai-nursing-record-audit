"""Evidence 核對：excerpt 必須在 record_id 的原文中，來源與欄位由程式回填。"""

from datetime import date

from app.core.enums import Verdict
from app.schemas.llm_structured import LlmEvidence, LlmFinding, RuleOutput
from app.services.audit.evidence import verify_output
from app.services.audit.records import SourceField, SourceRecord

ASSESSMENT = SourceRecord(
    record_id="assess-1",
    source="daily_physical_assessment",
    business_date=date(2026, 1, 2),
    time_text="2026-01-02 08:00:00",
    recorded_at=None,
    fields=(
        SourceField("呼吸音", "雙側呼吸音清，無囉音"),
        SourceField("意識", "清楚"),
    ),
)
RECORDS = {ASSESSMENT.record_id: ASSESSMENT}


def _output(verdict: str, *findings: LlmFinding) -> RuleOutput:
    return RuleOutput(verdict=verdict, summary="摘要", findings=list(findings))  # type: ignore[arg-type]


def _finding(verdict: str, *evidence: LlmEvidence) -> LlmFinding:
    return LlmFinding(item="呼吸音", verdict=verdict, message="訊息", evidence=list(evidence))  # type: ignore[arg-type]


def test_valid_excerpt_is_kept_and_source_and_field_are_backfilled() -> None:
    evidence = LlmEvidence(record_id="assess-1", excerpt="呼吸音：雙側呼吸音清")
    verified = verify_output(_output("WARNING", _finding("WARNING", evidence)), RECORDS)

    (item,) = verified.findings[0].evidence
    assert verified.verdict == Verdict.WARNING
    assert (item.source, item.field, item.record_id) == (
        "daily_physical_assessment",
        "呼吸音",
        "assess-1",
    )
    assert item.recorded_at is None


def test_excerpt_matching_ignores_whitespace() -> None:
    evidence = LlmEvidence(record_id="assess-1", excerpt="雙側 呼吸音   清")
    verified = verify_output(_output("WARNING", _finding("WARNING", evidence)), RECORDS)

    assert len(verified.findings[0].evidence) == 1


def test_fabricated_excerpt_is_dropped_and_warning_becomes_needs_review() -> None:
    evidence = LlmEvidence(record_id="assess-1", excerpt="雙側有明顯囉音")
    verified = verify_output(_output("WARNING", _finding("WARNING", evidence)), RECORDS)

    assert verified.findings[0].evidence == ()
    assert verified.findings[0].verdict == Verdict.NEEDS_REVIEW
    assert verified.verdict == Verdict.NEEDS_REVIEW


def test_unknown_record_id_is_dropped() -> None:
    evidence = LlmEvidence(record_id="not-exists", excerpt="雙側呼吸音清")
    verified = verify_output(_output("WARNING", _finding("WARNING", evidence)), RECORDS)

    assert verified.findings[0].evidence == ()
    assert verified.verdict == Verdict.NEEDS_REVIEW


def test_overall_pass_is_raised_when_a_finding_warns_with_evidence() -> None:
    evidence = LlmEvidence(record_id="assess-1", excerpt="意識：清楚")
    verified = verify_output(_output("PASS", _finding("WARNING", evidence)), RECORDS)

    assert verified.verdict == Verdict.WARNING


def test_warning_without_any_findings_becomes_needs_review() -> None:
    verified = verify_output(_output("WARNING"), RECORDS)

    assert verified.verdict == Verdict.NEEDS_REVIEW


def test_excerpt_matches_despite_noise_characters_and_time_field() -> None:
    """院方原文的變體選擇器不影響核對；院方的時間欄位也可以作為依據。"""
    record = SourceRecord(
        record_id="consult-1",
        source="consultation",
        business_date=date(2026, 1, 2),
        time_text="2026-01-02 16:22",
        recorded_at=None,
        fields=(SourceField("類別", "胸腔內科\U000e01b5(V:醫師甲)"),),
        source_label="會診",
    )
    output = RuleOutput(
        verdict="WARNING",
        summary="摘要",
        findings=[
            LlmFinding(
                item="胸腔內科",
                verdict="WARNING",
                message="請確認",
                evidence=[
                    LlmEvidence(record_id="consult-1", excerpt="胸腔內科(V:醫師甲)"),
                    LlmEvidence(record_id="consult-1", excerpt="16:22"),
                ],
            )
        ],
    )

    verified = verify_output(output, {record.record_id: record})

    evidence = verified.findings[0].evidence
    assert [item.field for item in evidence] == ["類別", None]
    assert evidence[0].source_label == "會診"
    assert evidence[0].time_text == "2026-01-02 16:22"
    assert verified.verdict == Verdict.WARNING
