"""LLM 輸出的依據核對（hallucination guard）。

excerpt 去除空白與雜訊字元後必須出現在 record_id 的原文中才保留；
來源、欄位、時間由程式依 record_id 回填，不採用 LLM 給的值。
WARNING 沒有任何有效依據時降為 NEEDS_REVIEW，絕不因此視為 PASS。
"""

from collections.abc import Mapping
from dataclasses import dataclass

from app.core.enums import Verdict
from app.schemas.audit import Evidence
from app.schemas.llm_structured import LlmEvidence, LlmFinding, RuleOutput
from app.services.audit.records import SourceRecord
from app.services.audit.severity import most_severe
from app.services.audit.text import squash


@dataclass(frozen=True)
class VerifiedFinding:
    """通過核對的發現；`evidence` 只含有效依據。"""

    item: str
    verdict: Verdict
    message: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True)
class VerifiedOutput:
    """通過核對的整體輸出。"""

    verdict: Verdict
    summary: str
    findings: tuple[VerifiedFinding, ...]


def verify_output(output: RuleOutput, records: Mapping[str, SourceRecord]) -> VerifiedOutput:
    """核對依據、降級沒有依據的 WARNING，並算出整體判定。"""
    findings = tuple(_verify_finding(finding, records) for finding in output.findings)
    has_evidence = any(finding.evidence for finding in findings)
    verdict = _overall_verdict(output.verdict, findings)
    if verdict == Verdict.WARNING and not has_evidence:
        verdict = Verdict.NEEDS_REVIEW
    return VerifiedOutput(verdict=verdict, summary=output.summary, findings=findings)


def _verify_finding(finding: LlmFinding, records: Mapping[str, SourceRecord]) -> VerifiedFinding:
    evidence = tuple(
        verified
        for verified in (_verify_one(item, records) for item in finding.evidence)
        if verified is not None
    )
    verdict = Verdict(finding.verdict)
    if verdict == Verdict.WARNING and not evidence:
        verdict = Verdict.NEEDS_REVIEW
    return VerifiedFinding(
        item=finding.item, verdict=verdict, message=finding.message, evidence=evidence
    )


def _verify_one(item: LlmEvidence, records: Mapping[str, SourceRecord]) -> Evidence | None:
    """依 record_id 找到紀錄並確認 excerpt 存在；找不到就丟棄（回傳 None）。"""
    record = records.get(item.record_id)
    excerpt = squash(item.excerpt)
    if record is None or not excerpt:
        return None
    for field in record.fields:
        candidates = (field.value, f"{field.label}：{field.value}", f"{field.label}{field.value}")
        if any(excerpt in squash(candidate) for candidate in candidates):
            return _evidence(record, field.label, item.excerpt)
    # 跨欄位的片段，或院方的時間欄位（如會診時間）
    if excerpt in squash(record.raw_text) or excerpt in squash(record.time_text):
        return _evidence(record, None, item.excerpt)
    return None


def _evidence(record: SourceRecord, field: str | None, excerpt: str) -> Evidence:
    return Evidence(
        source=record.source,
        source_label=record.source_label or record.source,
        record_id=record.record_id,
        field=field,
        business_date=record.business_date,
        time_text=record.time_text,
        recorded_at=record.recorded_at,
        excerpt=excerpt.strip(),
    )


def _overall_verdict(llm_verdict: str, findings: tuple[VerifiedFinding, ...]) -> Verdict:
    """整體判定取整體與各發現中較嚴重者，避免 LLM 把警示項目標成 PASS。"""
    verdicts = [Verdict(llm_verdict), *(finding.verdict for finding in findings)]
    return most_severe(verdicts)
