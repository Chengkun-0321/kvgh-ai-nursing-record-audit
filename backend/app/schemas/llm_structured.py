"""結構化 LLM 呼叫的請求與結果（gateway 與稽核規則共用的值物件）。"""

from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel


@dataclass(frozen=True)
class LLMRequest:
    """一次結構化呼叫：哪條規則、用哪個 prompt 模板與版本、模板變數。"""

    rule_code: str
    prompt_name: str
    prompt_version: str
    variables: Mapping[str, object]


@dataclass(frozen=True)
class LLMResult[T: BaseModel]:
    """結構化呼叫的結果；token 用量、成本、耗時取不到時為 `None`。"""

    parsed: T
    model: str
    # 例：`r02_copy_paste/v1`
    prompt_version: str
    system_prompt_version: int | None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    duration_ms: int | None = None
