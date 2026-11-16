"""ORM 紀錄 → 回應結構；狀態文字在此對照，前端不另算。"""

from collections.abc import Mapping

from app.core.enums import Verdict
from app.models.audit import AuditFinding, AuditRun
from app.schemas.audit import AuditFindingRead, AuditRunRead, Evidence
from app.services.audit.labels import AUDIT_RUN_STATUS_LABELS, VERDICT_LABELS
from app.services.audit.rules.base import AuditRule, LabelsFindings


def to_run_read(run: AuditRun, rule: AuditRule) -> AuditRunRead:
    """一次執行的回應結構（發現需已載入）。"""
    labels = rule.finding_labels(run.details) if isinstance(rule, LabelsFindings) else {}
    return AuditRunRead(
        id=run.id,
        rule_code=run.rule_code,
        rule_name=rule.name,
        patient_key=run.patient_key,
        business_date=run.business_date,
        status=run.status,
        status_label=AUDIT_RUN_STATUS_LABELS[run.status],
        status_reason=run.status_reason,
        verdict=run.verdict,
        verdict_label=VERDICT_LABELS[run.verdict] if run.verdict else None,
        summary=run.summary,
        findings=[_finding_read(finding, labels) for finding in run.findings],
        details=run.details,
        model=run.model,
        prompt_version=run.prompt_version,
        system_prompt_version=run.system_prompt_version,
        duration_ms=run.duration_ms,
        created_at=run.created_at,
    )


def _finding_read(finding: AuditFinding, labels: Mapping[str, str]) -> AuditFindingRead:
    return AuditFindingRead(
        position=finding.position,
        item=finding.item,
        verdict=finding.verdict,
        verdict_label=_finding_label(finding, labels),
        message=finding.message,
        evidence=[Evidence.model_validate(evidence) for evidence in finding.evidence],
    )


def _finding_label(finding: AuditFinding, labels: Mapping[str, str]) -> str:
    """規則的專屬文字只取代「無法判定」；其他判定一律用共同文字。"""
    default = VERDICT_LABELS[finding.verdict]
    if finding.verdict != Verdict.NEEDS_REVIEW:
        return default
    return labels.get(finding.item, default)
