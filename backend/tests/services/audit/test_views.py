"""稽核結果回應結構的顯示文字。"""

import uuid
from datetime import UTC, date, datetime

import pytest

from app.core.enums import AuditRunStatus, Verdict
from app.models.audit import AuditFinding, AuditRun
from app.services.audit.registry import RULE_REGISTRY
from app.services.audit.views import finding_verdict_label, to_run_read


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
        _finding(2, "處理", Verdict.PASS),
    ]

    assert _labels("R01", findings) == {
        "住院原因": "未見紀錄",
        "意識不清": "無法判定",
        "處理": "紀錄完整",
    }


def test_rule_label_does_not_replace_warning() -> None:
    assert _labels("R01", [_finding(0, "住院原因", Verdict.WARNING)]) == {"住院原因": "需確認"}


@pytest.mark.parametrize(
    "verdict,labels,expected",
    [
        (Verdict.PASS, {"項目甲": "寬限期中"}, "寬限期中"),
        (Verdict.PASS, {}, "紀錄完整"),
        (Verdict.NEEDS_REVIEW, {"項目甲": "未見紀錄"}, "未見紀錄"),
        (Verdict.WARNING, {"項目甲": "寬限期中"}, "需確認"),
        (Verdict.ERROR, {"項目甲": "寬限期中"}, "缺漏"),
    ],
)
def test_finding_label_respects_verdict(
    verdict: Verdict, labels: dict[str, str], expected: str
) -> None:
    """依判定與項目文字對照，確認顯示文字符合提醒判定的保護條件。"""
    finding = _finding(0, "項目甲", verdict)

    assert finding_verdict_label(finding, labels) == expected


def test_r06_pass_findings_use_grace_label_only_in_grace() -> None:
    """病患頁的寬限期項目顯示專屬文字，已見對應紀錄則維持共同文字。"""
    run = _run("R06", [_finding(0, "項目甲", Verdict.PASS), _finding(1, "項目乙", Verdict.PASS)])
    run.verdict = Verdict.PASS
    run.details = {
        "consultations": [
            {"item": "項目甲", "status": "IN_GRACE"},
            {"item": "項目乙", "status": "MATCHED"},
        ]
    }

    read = to_run_read(run, RULE_REGISTRY["R06"])

    assert [finding.verdict_label for finding in read.findings] == ["寬限期中", "紀錄完整"]


def test_rule_without_own_labels_keeps_common_text() -> None:
    assert _labels("R04", [_finding(0, "住院原因", Verdict.NEEDS_REVIEW)]) == {
        "住院原因": "無法判定"
    }
