"""R02 的紀錄整理與程式比對：回溯期間、類別對齊、相似度參考值。

相似度只是給 LLM 參考的數字，不是判定依據；判定全部交給 LLM（見 r02_copy_paste.py）。
比對前以共用的 `text.normalize_text` 正規化原文。
"""

import difflib
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Final

from app.services.audit.records import SourceRecord
from app.services.audit.text import normalize_text

TAG_LABEL: Final = "類別"
TUBE_LABEL: Final = "管路"
UNTAGGED_CATEGORY: Final = "（無類別）"
_NOT_COMPARABLE_TEXT: Final = "前幾日沒有同類別紀錄，無法比對"
_EMPTY_SCORE_TEXT: Final = "無（其中一方內容為空）"


@dataclass(frozen=True)
class CategoryComparison:
    """一個類別的比對：當日紀錄對上最近一個前日同類別紀錄。`prior` 為 None 表示無法比對。"""

    category: str
    today: SourceRecord
    prior: SourceRecord | None
    similarity: float | None


def window_start(business_date: date, lookback_days: int) -> date:
    """回溯期間的起日；期間含當日，天數至少為 1。"""
    return business_date - timedelta(days=max(lookback_days, 1) - 1)


def note_category(record: SourceRecord) -> str:
    """護理紀錄的類別（「類別」欄）；沒有類別時為 `UNTAGGED_CATEGORY`。"""
    for field in record.fields:
        if field.label == TAG_LABEL and field.value:
            return field.value
    return UNTAGGED_CATEGORY


def note_body(record: SourceRecord) -> str:
    """護理紀錄的內文：除了類別以外的所有欄位值。"""
    return "\n".join(field.value for field in record.fields if field.label != TAG_LABEL)


def tube_only(record: SourceRecord) -> SourceRecord | None:
    """只保留「管路」欄位的身評紀錄；沒有管路欄位或內容為空時回傳 None。

    record_id 不變，Evidence 仍可指回原紀錄；只有管路欄位會被送給 LLM。
    """
    tubes = tuple(field for field in record.fields if field.label == TUBE_LABEL and field.value)
    return replace(record, fields=tubes) if tubes else None


def similarity(before: str, after: str) -> float | None:
    """兩段原文正規化後的相似度（0 到 1，取兩位小數）；任一方為空則為 None。"""
    left, right = normalize_text(before), normalize_text(after)
    if not left or not right:
        return None
    ratio = difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()
    return round(ratio, 2)


def compare_notes(notes: Sequence[SourceRecord], today: date) -> list[CategoryComparison]:
    """當日每個類別與最近一個前日同類別紀錄比對。

    `notes` 須已限定在回溯期間內。同一日同類別最多一筆（院方資料特性）；
    若違反，取第一筆並不影響其他類別。
    """
    comparisons: list[CategoryComparison] = []
    for category, group in _group_by_category(notes).items():
        todays = [record for record in group if record.business_date == today]
        if not todays:
            continue
        prior = _latest_prior(group, today)
        score = similarity(note_body(prior), note_body(todays[0])) if prior is not None else None
        comparisons.append(CategoryComparison(category, todays[0], prior, score))
    return comparisons


def similarity_fact(comparison: CategoryComparison) -> dict[str, object]:
    """存入結果 details 的程式比對資料：類別、比對的前一日、相似度參考值。"""
    prior = comparison.prior
    return {
        "category": comparison.category,
        "compared_date": prior.business_date.isoformat() if prior is not None else None,
        "similarity": comparison.similarity,
    }


def render_alignment_block(comparisons: Sequence[CategoryComparison]) -> str:
    """類別對齊的文字區塊：每個當日類別一行，列出比對的前一日與程式相似度參考值。"""
    if not comparisons:
        return "（當日沒有護理紀錄）"
    return "\n".join(_alignment_line(comparison) for comparison in comparisons)


def _group_by_category(notes: Sequence[SourceRecord]) -> dict[str, list[SourceRecord]]:
    groups: dict[str, list[SourceRecord]] = {}
    for record in notes:
        groups.setdefault(note_category(record), []).append(record)
    return groups


def _latest_prior(group: Sequence[SourceRecord], today: date) -> SourceRecord | None:
    priors = [record for record in group if record.business_date < today]
    return max(priors, key=lambda record: record.business_date, default=None)


def _alignment_line(comparison: CategoryComparison) -> str:
    head = f"- 類別「{comparison.category}」：當日 {comparison.today.business_date.isoformat()}"
    if comparison.prior is None:
        return f"{head}；{_NOT_COMPARABLE_TEXT}"
    score = (
        f"{comparison.similarity:.2f}" if comparison.similarity is not None else _EMPTY_SCORE_TEXT
    )
    return (
        f"{head}；最近前日 {comparison.prior.business_date.isoformat()}；程式相似度參考值 {score}"
    )
