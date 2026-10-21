"""gateway.complete_structured 測試：B5、E8（格式重試）、E5（gateway 層）。

load_active_model_settings 與 litellm.acompletion 一律 mock，不發出網路請求。
"""

import copy
import importlib.util
import json
import sys
from collections.abc import AsyncIterator, Iterable
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import LLMNotConfiguredError
from app.schemas.llm_structured import LLMRequest
from app.services.audit.rules.r02_copy_paste import R02LLMOutput
from app.services.llm import gateway
from app.services.llm.gateway import LLMOutputError
from app.services.llm.prompt_loader import render_prompt


def _load_support() -> ModuleType:
    name = "r02_support"
    if name in sys.modules:
        return sys.modules[name]
    tests_root = Path(__file__).resolve().parents[2]
    path = tests_root / "fixtures" / "daily_packages" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


support = _load_support()

SYSTEM_PROMPT = "你是稽核助理"
LITELLM_MODEL = "openai/test-model"
VALID_JSON = json.dumps({"verdict": "PASS", "notes": [], "evidence": []})
INVALID_JSON = json.dumps({"verdict": "MAYBE", "notes": [], "evidence": []})
OUT_OF_RANGE_JSON = json.dumps(
    {
        "verdict": "WARNING",
        "notes": [
            {
                "record_id": "NPN-P001-0903-01",
                "similar_record_id": "NPN-P001-0902-01",
                "similarity_percent": 150,
                "issue_types": ["copy"],
            }
        ],
        "evidence": [],
    }
)


class _FakeCompletion:
    """假的 litellm.acompletion：依序回傳 contents，用完後重複最後一個。

    每次呼叫時複製 messages，避免 gateway 原地修改清單影響比對。
    """

    def __init__(self, contents: Iterable[str]) -> None:
        self.contents = list(contents)
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, *args: object, **kwargs: object) -> SimpleNamespace:
        recorded = dict(kwargs)
        recorded["messages"] = copy.deepcopy(kwargs.get("messages"))
        self.calls.append(recorded)
        index = min(len(self.calls), len(self.contents)) - 1
        message = SimpleNamespace(content=self.contents[index])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=message)],
            usage=None,
            model=LITELLM_MODEL,
        )


def _use_settings(
    monkeypatch: pytest.MonkeyPatch,
    system_prompt: str = SYSTEM_PROMPT,
    system_prompt_version: int | None = 3,
) -> None:
    settings = gateway.ActiveModelSettings(
        provider="openai",
        model=LITELLM_MODEL,
        api_key="sk-test-fake",
        api_base=None,
        timeout_seconds=30,
        system_prompt=system_prompt,
        system_prompt_version=system_prompt_version,
    )

    async def _fake_load(*_args: object, **_kwargs: object) -> gateway.ActiveModelSettings:
        return settings

    monkeypatch.setattr(gateway, "load_active_model_settings", _fake_load)


def _use_completion(monkeypatch: pytest.MonkeyPatch, contents: Iterable[str]) -> _FakeCompletion:
    fake = _FakeCompletion(contents)
    monkeypatch.setattr("litellm.acompletion", fake)
    monkeypatch.setattr("litellm.completion_cost", lambda *_a, **_k: 0.0)
    return fake


def _set_max_retries(monkeypatch: pytest.MonkeyPatch, value: int) -> None:
    monkeypatch.setenv("LLM_MAX_RETRIES", str(value))
    get_settings.cache_clear()


def _expected_prompt(request: LLMRequest) -> str:
    return render_prompt(request.prompt_name, request.prompt_version, request.variables)


@pytest.fixture
async def rule_request(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[LLMRequest]:
    """以假的 StructuredLLM 跑一次 P001 9/03 稽核，捕捉 R02 的 LLMRequest。"""
    root = support.prepare_data_dirs(tmp_path, monkeypatch)
    llm = support.FakeStructuredLLM()
    await support.run_r02(session, root, llm, patient_key="P001", business_date=date(2026, 9, 3))
    assert llm.calls == 1
    yield llm.requests[0]
    get_settings.cache_clear()


async def test_b5_messages_system_prompt_then_rule_prompt(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B5：訊息依序為共用 system prompt、規則 prompt（prompt_loader 渲染）。"""
    _use_settings(monkeypatch)
    fake = _use_completion(monkeypatch, [VALID_JSON])

    await gateway.complete_structured(rule_request, R02LLMOutput)

    messages = fake.calls[0]["messages"]
    assert messages[0] == {"role": "system", "content": SYSTEM_PROMPT}
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == _expected_prompt(rule_request)


async def test_b5_empty_system_prompt_is_not_sent(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B5：system prompt 為空時不送 system 訊息，但仍回傳設定的版本號。"""
    _use_settings(monkeypatch, system_prompt="", system_prompt_version=3)
    fake = _use_completion(monkeypatch, [VALID_JSON])

    result = await gateway.complete_structured(rule_request, R02LLMOutput)

    messages = fake.calls[0]["messages"]
    assert messages[0]["role"] == "user"
    assert all(item["role"] != "system" for item in messages)
    assert result.system_prompt_version == 3


async def test_b5_call_parameters(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B5：呼叫參數 temperature=0、model 為 openai/test-model。"""
    _use_settings(monkeypatch)
    fake = _use_completion(monkeypatch, [VALID_JSON])

    await gateway.complete_structured(rule_request, R02LLMOutput)

    assert fake.calls[0]["temperature"] == 0
    assert fake.calls[0]["model"] == "openai/test-model"


async def test_b5_retry_limit_then_raises_output_error(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B5：LLM_MAX_RETRIES=1 且永遠回不合法輸出 → 呼叫 2 次後拋 LLMOutputError。"""
    _set_max_retries(monkeypatch, 1)
    _use_settings(monkeypatch)
    fake = _use_completion(monkeypatch, [INVALID_JSON])

    with pytest.raises(LLMOutputError):
        await gateway.complete_structured(rule_request, R02LLMOutput)

    assert len(fake.calls) == 2


async def test_b5_zero_retries_raises_after_one_call(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B5 邊界：LLM_MAX_RETRIES=0 → 呼叫 1 次就拋 LLMOutputError。"""
    _set_max_retries(monkeypatch, 0)
    _use_settings(monkeypatch)
    fake = _use_completion(monkeypatch, ["這不是 JSON"])

    with pytest.raises(LLMOutputError):
        await gateway.complete_structured(rule_request, R02LLMOutput)

    assert len(fake.calls) == 1


async def test_b5_retry_succeeds_with_validation_error_attached(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """B5：第一次不合法、第二次合法 → 成功，呼叫 2 次。

    第二次附上驗證錯誤，messages 比第一次多。
    """
    _set_max_retries(monkeypatch, 1)
    _use_settings(monkeypatch)
    fake = _use_completion(monkeypatch, [INVALID_JSON, VALID_JSON])

    result = await gateway.complete_structured(rule_request, R02LLMOutput)

    assert isinstance(result.parsed, R02LLMOutput)
    assert len(fake.calls) == 2
    assert len(fake.calls[1]["messages"]) > len(fake.calls[0]["messages"])


async def test_b5_return_value(rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """B5：回傳 parsed、model、prompt_version、system_prompt_version。"""
    _use_settings(monkeypatch, system_prompt_version=3)
    _use_completion(monkeypatch, [VALID_JSON])

    result = await gateway.complete_structured(rule_request, R02LLMOutput)

    assert isinstance(result.parsed, R02LLMOutput)
    assert result.parsed.verdict == "PASS"
    assert result.model == "openai/test-model"
    assert result.prompt_version == "r02_copy_paste/v1"
    assert result.system_prompt_version == 3


async def test_e8_out_of_range_similarity_is_retried(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E8：第一次回 similarity_percent 150、第二次合法 → 重試後成功。"""
    _set_max_retries(monkeypatch, 1)
    _use_settings(monkeypatch)
    fake = _use_completion(monkeypatch, [OUT_OF_RANGE_JSON, VALID_JSON])

    result = await gateway.complete_structured(rule_request, R02LLMOutput)

    assert isinstance(result.parsed, R02LLMOutput)
    assert len(fake.calls) == 2


async def test_e5_not_configured_raises_without_calling_llm(
    rule_request: LLMRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E5（gateway 層）：沒有使用中的模型設定 → 拋 LLMNotConfiguredError。

    litellm.acompletion 不被呼叫。
    """

    async def _not_configured(*_args: object, **_kwargs: object) -> gateway.ActiveModelSettings:
        raise LLMNotConfiguredError()

    monkeypatch.setattr(gateway, "load_active_model_settings", _not_configured)
    fake = _use_completion(monkeypatch, [VALID_JSON])

    with pytest.raises(LLMNotConfiguredError):
        await gateway.complete_structured(rule_request, R02LLMOutput)

    assert fake.calls == []
