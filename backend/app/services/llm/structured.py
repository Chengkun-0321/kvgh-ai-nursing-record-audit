"""結構化輸出：渲染 prompt → 呼叫模型 → 驗證 JSON；格式不符時附上錯誤重試。

對外入口是 `gateway.complete_structured`。本模組不 import gateway，避免循環引用。
呼叫期間不占 DB 連線：讀完設定快照後 session 即結束交易。
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Final

import litellm
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import LlmProvider
from app.core.exceptions import LLMNotConfiguredError, LLMOutputError
from app.crud import llm_config as llm_config_crud
from app.schemas.llm_structured import LLMRequest, LLMResult
from app.services.llm import chatgpt_auth, prompt_loader
from app.services.llm.call_support import (
    CHATGPT_INSTRUCTIONS_LOCK,
    PreparedCall,
    apply_chatgpt_instructions,
    prepare_call,
    prepend_system_prompt,
    read_call_snapshot,
)
from app.services.llm.system_prompt_service import SystemPromptForCall

logger = logging.getLogger(__name__)

NOT_CONFIGURED_MESSAGE: Final = "尚未設定使用中的模型，請先至 LLM 設定頁新增並啟用一組模型"
OUTPUT_INVALID_MESSAGE: Final = "模型輸出未符合要求的格式，無法判定，請人工確認或更換模型"
OUTPUT_TRUNCATED_MESSAGE: Final = "模型輸出超過長度上限而被截斷，無法判定，請人工確認或更換模型"
# 回應因達到輸出上限而結束時的 finish_reason（LiteLLM 統一為 OpenAI 的值）
_FINISH_REASON_LENGTH: Final = "length"
# 回饋給模型的錯誤說明最多列幾項，避免重試訊息過長
_MAX_ERROR_ITEMS: Final = 5
_CORRECTION_TEMPLATE: Final = (
    "上一次的輸出不符合要求的格式（{details}）。請只輸出符合格式的 JSON，不要加入其他文字。"
)


class _ConcurrencyGate:
    """程序內的 LLM 併發閘門。

    `asyncio.Semaphore` 會綁定第一次使用它的 event loop，因此每個 loop 各自建立一個。
    """

    def __init__(self) -> None:
        self._semaphore: asyncio.Semaphore | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._limit = 0

    def for_running_loop(self, limit: int) -> asyncio.Semaphore:
        """取得目前 loop 的閘門；loop 或上限改變時重新建立。"""
        loop = asyncio.get_running_loop()
        if self._semaphore is None or self._loop is not loop or self._limit != limit:
            self._semaphore = asyncio.Semaphore(limit)
            self._loop = loop
            self._limit = limit
        return self._semaphore


_GATE: Final = _ConcurrencyGate()


@dataclass
class _Usage:
    """多次嘗試的累計用量；成本查不到時為 `None`，不影響結果。"""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost_usd: float | None = None
    attempts: int = 0
    _cost_parts: list[float] = field(default_factory=list)

    def add(self, response: Any) -> None:
        """加入一次回應的 token 與成本。"""
        self.attempts += 1
        usage = getattr(response, "usage", None)
        self.prompt_tokens = _sum_optional(
            self.prompt_tokens, getattr(usage, "prompt_tokens", None)
        )
        self.completion_tokens = _sum_optional(
            self.completion_tokens, getattr(usage, "completion_tokens", None)
        )
        cost = _completion_cost(response)
        if cost is not None:
            self._cost_parts.append(cost)
            self.cost_usd = sum(self._cost_parts)


async def complete_structured[T: BaseModel](
    session: AsyncSession, request: LLMRequest, output_schema: type[T]
) -> LLMResult[T]:
    """以使用中的模型設定執行一次結構化呼叫。

    Args:
        session: DB session；只用來讀取設定與共用 system prompt，讀完即結束交易。
        request: 規則代碼、prompt 名稱與版本、模板變數。
        output_schema: 期望的輸出結構（通常是 `RuleOutput` 的子類別）。

    Returns:
        驗證通過的結果與用量、耗時、prompt 摘要。

    Raises:
        LLMNotConfiguredError: 沒有使用中的模型設定。
        LLMOutputError: 重試後仍不符合格式；呼叫端必須轉為 NEEDS_REVIEW，不可視為 PASS。
        LLMConnectionError: 模型服務連線、驗證或額度等錯誤（由 LiteLLM 例外轉成）。
    """
    active = await llm_config_crud.get_active(session)
    if active is None:
        raise LLMNotConfiguredError(NOT_CONFIGURED_MESSAGE)
    snapshot = await read_call_snapshot(session, active.id)
    if snapshot.config.provider == LlmProvider.CHATGPT:
        await chatgpt_auth.ensure_access_token()

    call = prepare_call(snapshot.config, snapshot.system_prompt)
    call.kwargs["temperature"] = 0
    call.kwargs["num_retries"] = get_settings().LLM_STRUCTURED_NUM_RETRIES
    # Ollama 由 LiteLLM 轉成 num_predict；不支援的服務因 drop_params 而略過
    call.kwargs["max_tokens"] = get_settings().LLM_MAX_OUTPUT_TOKENS
    prompt = _preprocess(
        prompt_loader.render_prompt(request.prompt_name, request.prompt_version, request.variables)
    )
    started = time.perf_counter()
    parsed, usage = await _run_attempts(
        call, snapshot_prompt=snapshot.system_prompt, prompt=prompt, output_schema=output_schema
    )
    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "結構化呼叫完成：rule=%s prompt=v%s attempts=%s model=%s",
        request.rule_code,
        request.prompt_version,
        usage.attempts,
        call.litellm_model,
    )
    return LLMResult[T](
        parsed=parsed,
        model=call.litellm_model,
        prompt_version=request.prompt_version,
        system_prompt_version=call.system_prompt_version,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cost_usd=usage.cost_usd,
        duration_ms=duration_ms,
        input_digest=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        attempts=usage.attempts,
    )


async def _run_attempts[T: BaseModel](
    call: PreparedCall,
    *,
    snapshot_prompt: SystemPromptForCall | None,
    prompt: str,
    output_schema: type[T],
) -> tuple[T, _Usage]:
    """第一次呼叫加上格式重試；重試次數上限為 `LLM_MAX_RETRIES`。"""
    max_attempts = get_settings().LLM_MAX_RETRIES + 1
    usage = _Usage()
    history: list[dict[str, str]] = [{"role": "user", "content": prompt}]
    for attempt in range(1, max_attempts + 1):
        response = await _call_model(call, snapshot_prompt, history)
        usage.add(response)
        if _is_truncated(response):
            # 同一模型、同一輸入重試多半再被截斷，只會多耗時間；直接結束，不做格式重試
            logger.warning(
                "結構化輸出達上限被截斷：attempt=%s/%s completion_tokens=%s max_tokens=%s",
                attempt,
                max_attempts,
                getattr(getattr(response, "usage", None), "completion_tokens", None),
                call.kwargs.get("max_tokens"),
            )
            raise LLMOutputError(OUTPUT_TRUNCATED_MESSAGE)
        text = _message_text(response)
        try:
            return output_schema.model_validate_json(_strip_code_fence(text)), usage
        except ValidationError as error:
            # 重試訊息與 log 只含欄位位置與錯誤類型，不含模型輸出內容
            logger.warning("結構化輸出格式不符：attempt=%s/%s", attempt, max_attempts)
            history = [
                *history,
                {"role": "assistant", "content": text},
                {"role": "user", "content": _correction_message(error)},
            ]
    raise LLMOutputError(OUTPUT_INVALID_MESSAGE)


async def _call_model(
    call: PreparedCall,
    system_prompt: SystemPromptForCall | None,
    history: list[dict[str, str]],
) -> Any:
    """非串流呼叫，受 `LLM_MAX_CONCURRENCY` 限制；ChatGPT 指示的互斥只在這裡。"""
    request: dict[str, Any] = {
        "messages": prepend_system_prompt(history, system_prompt),
        "response_format": {"type": "json_object"},
        **call.kwargs,
    }
    gate = _GATE.for_running_loop(get_settings().LLM_MAX_CONCURRENCY)
    async with gate:
        if call.config.provider != LlmProvider.CHATGPT:
            return await litellm.acompletion(**request)
        async with CHATGPT_INSTRUCTIONS_LOCK:
            apply_chatgpt_instructions(system_prompt)
            return await litellm.acompletion(**request)


def _preprocess(prompt: str) -> str:
    """送出前的處理點：目前原樣傳遞，未來在這裡插入去識別化（見 ADR 0002）。"""
    return prompt


def _message_text(response: Any) -> str:
    """取出第一個回應的文字；沒有內容時為空字串（之後會被判為格式不符）。"""
    content = response.choices[0].message.content
    return content if isinstance(content, str) else ""


def _is_truncated(response: Any) -> bool:
    """回應是否因達到輸出 token 上限而結束（而非模型自行結束）。"""
    return getattr(response.choices[0], "finish_reason", None) == _FINISH_REASON_LENGTH


def _strip_code_fence(text: str) -> str:
    """模型有時會以 ```json 包住 JSON；去掉外層的圍欄再解析。"""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _correction_message(error: ValidationError) -> str:
    """把驗證錯誤轉成給模型的更正說明：只列欄位位置與錯誤說明，不含輸入值。"""
    items = [
        f"{'.'.join(str(part) for part in item['loc']) or '根層'}：{item['msg']}"
        for item in error.errors(include_input=False, include_url=False)[:_MAX_ERROR_ITEMS]
    ]
    return _CORRECTION_TEMPLATE.format(details="；".join(items))


def _completion_cost(response: Any) -> float | None:
    """以 LiteLLM 價格表計算成本；價格表沒有此模型時回傳 `None`。"""
    try:
        return float(litellm.completion_cost(completion_response=response))
    except Exception:
        # 價格查不到不應讓稽核失敗；只是該次沒有成本數字
        return None


def _sum_optional(total: int | None, value: object) -> int | None:
    if not isinstance(value, int):
        return total
    return value if total is None else total + value
