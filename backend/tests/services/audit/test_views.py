"""稽核結果回應結構的顯示文字。"""

import uuid
from datetime import UTC, date, datetime

from app.core.enums import AuditRunStatus, Verdict
from app.models.audit import AuditFinding, AuditRun
from app.services.audit.registry import RULE_REGISTRY
from app.services.audit.views import to_run_read


def _finding(position: int, item: str, verdict: Verdict) -> AuditFinding:
    return AuditFinding(
        position=position, item=item, verdict=verdict, message="請確認", evidence=[]
    )


def _run(rule_code: str, findings: list[AuditFinding]) -> AuditRun:
    elements = [
        {"element": "住院原因", "mentioned": False},
        {"element": "處理", "mentioned": True},
    ]
    return AuditRun(
        id=uuid.uuid4(),
        created_at=datetime(2026, 11, 16, tzinfo=UTC),
        rule_code=rule_code,
        patient_key="05060000",
        business_date=date(2026, 11, 5),
        status=AuditRunStatus.COMPLETED,
        verdict=Verdict.WARNING,
        details={"elements": elements},
        findings=findings,
    )


def _labels(rule_code: str, findings: list[AuditFinding]) -> dict[str, str]:
    read = to_run_read(_run(rule_code, findings), RULE_REGISTRY[rule_code])
    return {finding.item: finding.verdict_label for finding in read.findings}


def test_r01_unmentioned_element_is_labelled_as_not_recorded() -> None:
    findings = [
        _finding(0, "住院原因", Verdict.NEEDS_REVIEW),
        _finding(1, "意識不清", Verdict.NEEDS_REVIEW),
    ]

    assert _labels("R01", findings) == {"住院原因": "未見紀錄", "意識不清": "無法判定"}


def test_rule_label_does_not_replace_other_verdicts() -> None:
    assert _labels("R01", [_finding(0, "住院原因", Verdict.WARNING)]) == {"住院原因": "需確認"}


def test_rule_without_own_labels_keeps_common_text() -> None:
    assert _labels("R04", [_finding(0, "住院原因", Verdict.NEEDS_REVIEW)]) == {
        "住院原因": "無法判定"
    }
