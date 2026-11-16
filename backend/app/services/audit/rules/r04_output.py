"""R04 的專屬輸出結構：LLM 認定的異常項目清單，存入結果的 details。

獨立成模組，讓 `r04_checks` 可以引用而不與規則模組循環 import。
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.llm_structured import RuleOutput

# FOUND：異常，且當日護理紀錄有相應書寫；NOT_FOUND：異常，但未見相應書寫；
# UNCERTAIN：無法確定身評是否異常，或無法確定護理紀錄是否相應（需人工確認，不視為 NOT_FOUND）
FollowupStatus = Literal["FOUND", "NOT_FOUND", "UNCERTAIN"]


class FlaggedItem(BaseModel):
    """LLM 認定為異常、或無法確定是否異常的一個身評項目。"""

    item: str
    status: FollowupStatus
    reason: str = ""


class R04Output(RuleOutput):
    """R04 的輸出：共同欄位加上 `flagged_items`，讓護理師看得到判斷過程。"""

    flagged_items: list[FlaggedItem] = Field(default_factory=list)
