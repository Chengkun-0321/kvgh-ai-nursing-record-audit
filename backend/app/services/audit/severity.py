"""稽核判定的嚴重度比較：整體判定（evidence）與病床狀態（ward_board_status）共用同一份排序。"""

from collections.abc import Iterable
from typing import Final

from app.core.enums import Verdict

# 由低到高；ERROR 這一版不會由 LLM 產生，仍保留在最高以備日後分級
VERDICT_SEVERITY: Final[dict[Verdict, int]] = {
    Verdict.PASS: 0,
    Verdict.NEEDS_REVIEW: 1,
    Verdict.WARNING: 2,
    Verdict.ERROR: 3,
}


def most_severe(verdicts: Iterable[Verdict]) -> Verdict:
    """取最嚴重的判定；呼叫端需確認清單非空。"""
    return max(verdicts, key=lambda verdict: VERDICT_SEVERITY[verdict])
