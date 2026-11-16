"""稽核測試共用的假結果建立函式（不呼叫 LLM）。"""

from typing import Any

from pydantic import BaseModel

from app.schemas.llm_structured import LLMResult, RuleOutput


def make_result(parsed: BaseModel) -> LLMResult[RuleOutput]:
    """組出與 gateway 相同形狀的結果，用量與耗時為固定的假值。"""
    return LLMResult[RuleOutput](
        parsed=parsed,  # type: ignore[arg-type]
        model="ollama_chat/test-model",
        prompt_version=1,
        system_prompt_version=None,
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=None,
        duration_ms=3,
        input_digest="0" * 64,
        attempts=1,
    )


def payload_for(schema: type[BaseModel], payload: dict[str, Any]) -> BaseModel:
    """依規則的輸出結構驗證假輸出，與正式路徑相同。"""
    return schema.model_validate(payload)
