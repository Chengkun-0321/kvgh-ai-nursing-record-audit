"""結構化 LLM 呼叫的輸入與輸出：稽核規則以 `RuleOutput` 為共同輸出，專屬欄位由子類別加上。"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# LLM 只允許回傳這三種判定；ERROR 保留給未來客觀可驗證的判定，這一版不會出現（見 audit-rules.md）
LlmVerdict = Literal["PASS", "WARNING", "NEEDS_REVIEW"]


class LlmEvidence(BaseModel):
    """LLM 指出的依據：只給 record_id 與原文片段，來源、欄位、時間由程式依 record_id 回填。"""

    record_id: str
    excerpt: str


class LlmFinding(BaseModel):
    """一個檢查項目的發現。"""

    item: str
    verdict: LlmVerdict
    message: str
    evidence: list[LlmEvidence] = Field(default_factory=list)


class RuleOutput(BaseModel):
    """所有稽核規則共同的 LLM 輸出；規則可繼承並加上專屬欄位（存入結果的 details）。"""

    verdict: LlmVerdict
    summary: str
    findings: list[LlmFinding] = Field(default_factory=list)


class LLMRequest(BaseModel):
    """一次結構化呼叫：規則代碼、prompt 名稱與版本、模板變數（皆為字串）。"""

    model_config = ConfigDict(frozen=True)

    rule_code: str
    prompt_name: str = Field(pattern=r"^[a-z0-9_]+$")
    prompt_version: int = Field(ge=1)
    variables: dict[str, str]


class LLMResult[T: BaseModel](BaseModel):
    """結構化呼叫的結果；`input_digest` 為渲染後 prompt 的 sha256，不存全文。"""

    model_config = ConfigDict(frozen=True)

    parsed: T
    model: str
    prompt_version: int
    system_prompt_version: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    cost_usd: float | None
    duration_ms: int
    input_digest: str
    attempts: int
