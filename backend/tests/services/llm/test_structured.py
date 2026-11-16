"""結構化輸出：成功、格式重試、重試耗盡、無使用中設定。LLM 一律 mock，不發出網路請求。"""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import LLMNotConfiguredError, LLMOutputError
from app.schemas.llm_structured import LLMRequest, RuleOutput
from app.services.llm import prompt_loader, structured
from tests.services.llm.gateway_helpers import create_config

REQUEST = LLMRequest(
    rule_code="R03",
    prompt_name="r03_admission_completeness",
    prompt_version=1,
    variables={"checklist_block": "個人病史：沒有填寫"},
)
VALID_OUTPUT = {"verdict": "PASS", "summary": "完整", "findings": []}


def _response(content: str | None) -> SimpleNamespace:
    message = SimpleNamespace(content=content)
    usage = SimpleNamespace(prompt_tokens=11, completion_tokens=7)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


def _fake_acompletion(responses: list[str | None], calls: list[dict[str, Any]]) -> Any:
    queue = list(responses)

    async def fake(**kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return _response(queue.pop(0))

    return fake


@pytest.fixture(autouse=True)
def fake_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """不依賴 prompt 檔案內容，只測結構化呼叫本身。"""
    monkeypatch.setattr(prompt_loader, "render_prompt", lambda *_args, **_kwargs: "PROMPT")


async def test_valid_json_returns_parsed_result_with_usage(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_config(session)
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        structured.litellm, "acompletion", _fake_acompletion([json.dumps(VALID_OUTPUT)], calls)
    )

    result = await structured.complete_structured(session, REQUEST, RuleOutput)

    assert result.parsed == RuleOutput(verdict="PASS", summary="完整", findings=[])
    assert result.attempts == 1
    assert (result.prompt_tokens, result.completion_tokens) == (11, 7)
    assert result.cost_usd is None  # 測試用的假回應不在價格表內，成本留空而非失敗
    assert calls[0]["temperature"] == 0
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["messages"] == [{"role": "user", "content": "PROMPT"}]


async def test_code_fence_around_json_is_accepted(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_config(session)
    fenced = f"```json\n{json.dumps(VALID_OUTPUT)}\n```"
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(structured.litellm, "acompletion", _fake_acompletion([fenced], calls))

    result = await structured.complete_structured(session, REQUEST, RuleOutput)

    assert result.attempts == 1


async def test_format_error_is_retried_with_correction_that_omits_output_value(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_config(session)
    bad_verdict = json.dumps({"verdict": "ERROR", "summary": "x", "findings": []})
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        structured.litellm,
        "acompletion",
        _fake_acompletion([bad_verdict, json.dumps(VALID_OUTPUT)], calls),
    )

    result = await structured.complete_structured(session, REQUEST, RuleOutput)

    assert result.attempts == 2
    retry_messages = calls[1]["messages"]
    correction = retry_messages[-1]["content"]
    assert retry_messages[-2] == {"role": "assistant", "content": bad_verdict}
    assert "verdict" in correction
    # 更正訊息只列欄位與錯誤說明，不回傳輸入值
    assert "ERROR" not in correction


async def test_retries_are_exhausted_then_output_error_is_raised(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    await create_config(session)
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        structured.litellm, "acompletion", _fake_acompletion(["not json"] * 3, calls)
    )

    with pytest.raises(LLMOutputError):
        await structured.complete_structured(session, REQUEST, RuleOutput)

    # 第一次呼叫加上 LLM_MAX_RETRIES（預設 2）次重試
    assert len(calls) == 3


async def test_missing_active_config_raises_not_configured(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(structured.litellm, "acompletion", _fake_acompletion([], calls))

    with pytest.raises(LLMNotConfiguredError):
        await structured.complete_structured(session, REQUEST, RuleOutput)

    assert calls == []
