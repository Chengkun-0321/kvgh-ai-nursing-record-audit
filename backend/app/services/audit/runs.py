"""把核對後的結果組成 `AuditRun` 紀錄（不含 DB 操作；寫入在 crud、交易在 service）。"""

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.core.enums import AuditRunStatus, Verdict
from app.models.audit import AuditFinding, AuditRun
from app.schemas.llm_structured import LLMResult
from app.services.audit.evidence import VerifiedOutput


@dataclass(frozen=True)
class RunTarget:
    """一次執行的對象：規則、病患、寫入與查詢用的稽核日。"""

    rule_code: str
    patient_key: str
    business_date: date


@dataclass(frozen=True)
class RunMeta:
    """LLM 呼叫的紀錄資訊（不含 prompt 與輸出內容）。"""

    model: str
    prompt_version: int
    system_prompt_version: int | None
    input_digest: str
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float | None
    duration_ms: int

    @classmethod
    def from_result(cls, result: LLMResult[Any]) -> "RunMeta":
        """由 gateway 的結果取出紀錄資訊。"""
        return cls(
            model=result.model,
            prompt_version=result.prompt_version,
            system_prompt_version=result.system_prompt_version,
            input_digest=result.input_digest,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
            cost_usd=result.cost_usd,
            duration_ms=result.duration_ms,
        )


def status_run(target: RunTarget, status: AuditRunStatus, reason: str) -> AuditRun:
    """不呼叫 LLM 的結果：不適用、資料未提供、執行失敗。"""
    return AuditRun(**_base(target), status=status, status_reason=reason, findings=[])


def needs_review_run(target: RunTarget, reason: str) -> AuditRun:
    """LLM 輸出無法通過格式或規則驗證：COMPLETED 且判定為 NEEDS_REVIEW，不視為 PASS。"""
    run = AuditRun(
        **_base(target),
        status=AuditRunStatus.COMPLETED,
        status_reason=reason,
        verdict=Verdict.NEEDS_REVIEW,
        summary=reason,
        findings=[],
    )
    return run


def completed_run(
    target: RunTarget,
    verified: VerifiedOutput,
    details: dict[str, object] | None,
    meta: RunMeta,
) -> AuditRun:
    """LLM 結果通過核對後的完整紀錄。"""
    run = AuditRun(
        **_base(target),
        status=AuditRunStatus.COMPLETED,
        verdict=verified.verdict,
        summary=verified.summary,
        details=details,
        **_meta_fields(meta),
    )
    run.findings = [
        AuditFinding(
            position=position,
            item=finding.item,
            verdict=finding.verdict,
            message=finding.message,
            evidence=[evidence.model_dump(mode="json") for evidence in finding.evidence],
        )
        for position, finding in enumerate(verified.findings)
    ]
    return run


def _base(target: RunTarget) -> dict[str, object]:
    return {
        "rule_code": target.rule_code,
        "patient_key": target.patient_key,
        "business_date": target.business_date,
    }


def _meta_fields(meta: RunMeta) -> dict[str, object]:
    return {
        "model": meta.model,
        "prompt_version": meta.prompt_version,
        "system_prompt_version": meta.system_prompt_version,
        "input_digest": meta.input_digest,
        "prompt_tokens": meta.prompt_tokens,
        "completion_tokens": meta.completion_tokens,
        "cost_usd": meta.cost_usd,
        "duration_ms": meta.duration_ms,
    }
