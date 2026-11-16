"""R04 專屬輸出驗證：身評項目名稱、判定與 finding 的對應、依據來源、用語。

任一項不符即拋出 `LLMOutputError`，結果轉為 NEEDS_REVIEW，絕不視為 PASS。
錯誤訊息不含病歷內容（只描述違反的規則）。
"""

from collections.abc import Iterable, Sequence
from typing import Final

from app.core.exceptions import LLMOutputError
from app.schemas.llm_structured import LlmFinding
from app.services.audit.records import SourceRecord
from app.services.audit.rules.r04_output import FlaggedItem, FollowupStatus, R04Output

_ITEM_MESSAGE: Final = "模型輸出的身評項目與規定不符，無法判定"
_FINDING_MESSAGE: Final = "模型輸出的判定與異常項目不一致，無法判定"
_SOURCE_MESSAGE: Final = "模型輸出的依據不是身評紀錄，無法判定"
_WORDING_MESSAGE: Final = "模型輸出用語不符合提醒原則，無法判定"
# 狀態 → 應有的 finding 判定；FOUND 只允許 PASS（或不列）
_EXPECTED_VERDICT: Final[dict[str, str]] = {"NOT_FOUND": "WARNING", "UNCERTAIN": "NEEDS_REVIEW"}
# 院方與 llm.md 的提醒用語規定：不得指責護理師寫錯或漏寫
_FORBIDDEN_WORDS: Final = ("寫錯", "漏寫", "違規", "忘記")


def assessment_item_names(assessment_records: Iterable[SourceRecord]) -> list[str]:
    """身評欄位名稱，依院方原順序、去除重複。"""
    return list(
        dict.fromkeys(field.label for record in assessment_records for field in record.fields)
    )


def validate_r04_output(output: R04Output, assessment_records: Sequence[SourceRecord]) -> None:
    """依 R04 的規定核對 LLM 輸出。

    Raises:
        LLMOutputError: 項目名稱、判定對應、依據來源或用語不符。
    """
    names = assessment_item_names(assessment_records)
    assessment_ids = {record.record_id for record in assessment_records}
    _check_flagged_items(output.flagged_items, names)
    _check_findings(output.findings, output.flagged_items)
    _check_evidence_sources(output.findings, output.flagged_items, assessment_ids)
    _check_wording(output)


def _check_flagged_items(flagged: Sequence[FlaggedItem], names: list[str]) -> None:
    items = [entry.item for entry in flagged]
    if any(item not in names for item in items) or len(set(items)) != len(items):
        raise LLMOutputError(_ITEM_MESSAGE)


def _check_findings(findings: Sequence[LlmFinding], flagged: Sequence[FlaggedItem]) -> None:
    by_item = _findings_by_item(findings)
    statuses = {entry.item: entry.status for entry in flagged}
    if set(by_item) - set(statuses):
        raise LLMOutputError(_FINDING_MESSAGE)
    for item, status in statuses.items():
        _check_one_finding(status, by_item.get(item))


def _findings_by_item(findings: Sequence[LlmFinding]) -> dict[str, LlmFinding]:
    by_item: dict[str, LlmFinding] = {}
    for finding in findings:
        if finding.item in by_item:
            raise LLMOutputError(_FINDING_MESSAGE)
        by_item[finding.item] = finding
    return by_item


def _check_one_finding(status: FollowupStatus, finding: LlmFinding | None) -> None:
    if status == "FOUND":
        # 有相應紀錄的項目可以不列；若列出，只能是 PASS
        if finding is not None and finding.verdict != "PASS":
            raise LLMOutputError(_FINDING_MESSAGE)
        return
    if finding is None or finding.verdict != _EXPECTED_VERDICT[status]:
        raise LLMOutputError(_FINDING_MESSAGE)


def _check_evidence_sources(
    findings: Sequence[LlmFinding], flagged: Sequence[FlaggedItem], assessment_ids: set[str]
) -> None:
    """未找到相應紀錄或無法判斷的項目，依據必須指向身評紀錄（不得引用護理紀錄或輔助資料）。"""
    statuses = {entry.item: entry.status for entry in flagged}
    for finding in findings:
        if statuses.get(finding.item) == "FOUND":
            continue
        if any(evidence.record_id not in assessment_ids for evidence in finding.evidence):
            raise LLMOutputError(_SOURCE_MESSAGE)


def _check_wording(output: R04Output) -> None:
    texts = [output.summary, *(finding.message for finding in output.findings)]
    if any(word in text for text in texts for word in _FORBIDDEN_WORDS):
        raise LLMOutputError(_WORDING_MESSAGE)
