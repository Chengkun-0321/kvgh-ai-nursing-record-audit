"""向模型服務查詢可用模型清單（只查清單，不呼叫模型，不 import litellm）。

LiteLLM 內建的 `get_valid_models` 為同步呼叫、失敗時一律回傳空清單（Ollama 甚至改回傳內建清單），
無法告訴使用者失敗原因，所以改以 httpx 直接查詢各服務的清單 API。
由 gateway 解密金鑰後呼叫，本模組不讀 DB。
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.enums import LlmProvider
from app.core.exceptions import LLMConnectionError
from app.schemas.available_model import AvailableModel

_TIMEOUT_SECONDS: Final = 10
OPENAI_API_BASE: Final = "https://api.openai.com/v1"
GEMINI_API_BASE: Final = "https://generativelanguage.googleapis.com/v1beta"
_GEMINI_PAGE_SIZE: Final = 1000
# Gemini 以支援的方法區分：能 generateContent 的才是對話模型
_GEMINI_CHAT_METHOD: Final = "generateContent"
_GEMINI_NAME_PREFIX: Final = "models/"
_CODEX_VISIBLE: Final = "list"

_STATUS_MESSAGES: Final[Mapping[int, str]] = MappingProxyType(
    {
        httpx.codes.BAD_REQUEST: "服務拒絕此請求，請確認 API 金鑰是否正確",
        httpx.codes.UNAUTHORIZED: "API 金鑰無效或已過期，請確認金鑰",
        httpx.codes.FORBIDDEN: "此金鑰沒有查詢模型清單的權限，請確認帳戶或專案設定",
        httpx.codes.NOT_FOUND: (
            "此位址沒有提供模型清單，請確認 API 位址（OpenAI 相容伺服器通常以 /v1 結尾）"
        ),
    }
)


# 可用於對話的 LiteLLM 模式（Codex 系列為 responses）
CHAT_MODES: Final = frozenset({"chat", "responses"})
# 雲端服務的官方清單含向量、語音、影像模型，只保留對話模型；本地伺服器照實列出
CHAT_FILTERED_PROVIDERS: Final = frozenset({LlmProvider.OPENAI, LlmProvider.GEMINI})
# LiteLLM 價格表尚未收錄的新模型，以名稱排除明顯不是對話用的模型
_NON_CHAT_KEYWORDS: Final = (
    "embed",
    "tts",
    "whisper",
    "transcribe",
    "dall-e",
    "image",
    "moderation",
    "realtime",
    "audio",
    "sora",
    "veo",
    "aqa",
)


def is_chat_model(model_id: str, mode: str | None) -> bool:
    """判斷是否為對話模型。

    Args:
        model_id: 服務回傳的模型 ID。
        mode: LiteLLM 價格表記載的模式；未收錄時為 `None`，改以名稱判斷。
    """
    if mode is not None:
        return mode in CHAT_MODES
    lowered = model_id.lower()
    return not any(keyword in lowered for keyword in _NON_CHAT_KEYWORDS)


class ServiceUnreachableError(LLMConnectionError):
    """連不上服務（未啟動、逾時）；換路徑重試也沒有意義。"""


class ListingUnauthorizedError(LLMConnectionError):
    """金鑰或登入 token 無效（HTTP 401／403）。"""


class ListingNotFoundError(LLMConnectionError):
    """主機有回應，但該路徑不是預期格式的模型清單（用於偵測本地伺服器類型）。"""


@dataclass(frozen=True)
class ListingTarget:
    """要查詢的服務；`api_base` 已套用預設值，`api_key` 為明文（僅在查詢當下存在）。"""

    provider: LlmProvider
    api_base: str | None
    api_key: str | None
    # ChatGPT 訂閱以登入 token 組成的標頭與 client_version 查詢
    headers: Mapping[str, str] = field(default_factory=dict)
    params: Mapping[str, str] = field(default_factory=dict)


class _OllamaModel(BaseModel):
    name: str


class _OllamaTags(BaseModel):
    models: list[_OllamaModel]


class _OpenAIModel(BaseModel):
    id: str


class _OpenAIModelList(BaseModel):
    data: list[_OpenAIModel]


class _GeminiModel(BaseModel):
    name: str
    display_name: str | None = Field(default=None, alias="displayName")
    methods: list[str] = Field(default_factory=list, alias="supportedGenerationMethods")


class _GeminiModelList(BaseModel):
    models: list[_GeminiModel]


class _CodexModel(BaseModel):
    slug: str
    display_name: str | None = None
    # list＝顯示在模型選單；hide／none 為帳號不可選或內部用
    visibility: str = _CODEX_VISIBLE
    priority: int = 0


class _CodexModelList(BaseModel):
    models: list[_CodexModel]


@dataclass(frozen=True)
class _ListRequest:
    url: str
    parse: Callable[[object], list[AvailableModel]]
    headers: Mapping[str, str] = field(default_factory=dict)
    params: Mapping[str, str | int] = field(default_factory=dict)


def _parse_ollama(payload: object) -> list[AvailableModel]:
    tags = _OllamaTags.model_validate(payload)
    return [AvailableModel(id=model.name) for model in tags.models]


def _parse_openai(payload: object) -> list[AvailableModel]:
    listing = _OpenAIModelList.model_validate(payload)
    return [AvailableModel(id=model.id) for model in listing.data]


def _parse_gemini(payload: object) -> list[AvailableModel]:
    listing = _GeminiModelList.model_validate(payload)
    return [
        AvailableModel(id=model.name.removeprefix(_GEMINI_NAME_PREFIX), label=model.display_name)
        for model in listing.models
        if _GEMINI_CHAT_METHOD in model.methods
    ]


def _parse_codex(payload: object) -> list[AvailableModel]:
    listing = _CodexModelList.model_validate(payload)
    # 依 Codex 模型選單的排序（priority 小的在前），只保留帳號可選的模型
    visible = sorted(
        (model for model in listing.models if model.visibility == _CODEX_VISIBLE),
        key=lambda model: model.priority,
    )
    return [AvailableModel(id=model.slug, label=model.display_name) for model in visible]


def _bearer(api_key: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _ollama_request(target: ListingTarget) -> _ListRequest:
    return _ListRequest(url=f"{target.api_base}/api/tags", parse=_parse_ollama)


def _openai_compatible_request(target: ListingTarget) -> _ListRequest:
    return _ListRequest(
        url=f"{target.api_base}/models", parse=_parse_openai, headers=_bearer(target.api_key)
    )


def _openai_request(target: ListingTarget) -> _ListRequest:
    return _ListRequest(
        url=f"{OPENAI_API_BASE}/models", parse=_parse_openai, headers=_bearer(target.api_key)
    )


def _gemini_request(target: ListingTarget) -> _ListRequest:
    # 金鑰放 header 而非 query string，避免出現在 proxy 或伺服器的 URL log
    return _ListRequest(
        url=f"{GEMINI_API_BASE}/models",
        parse=_parse_gemini,
        headers={"x-goog-api-key": target.api_key or ""},
        params={"pageSize": _GEMINI_PAGE_SIZE},
    )


def _chatgpt_request(target: ListingTarget) -> _ListRequest:
    # 與 Codex CLI 相同：GET {Codex 後端}/models?client_version=…，回傳此帳號可用的模型
    return _ListRequest(
        url=f"{target.api_base}/models",
        parse=_parse_codex,
        headers=target.headers,
        params=target.params,
    )


_REQUEST_BUILDERS: Final = MappingProxyType(
    {
        LlmProvider.CHATGPT: _chatgpt_request,
        LlmProvider.OLLAMA: _ollama_request,
        LlmProvider.OPENAI_COMPATIBLE: _openai_compatible_request,
        LlmProvider.OPENAI: _openai_request,
        LlmProvider.GEMINI: _gemini_request,
    }
)


async def fetch_models(target: ListingTarget) -> list[AvailableModel]:
    """查詢服務目前提供的模型。

    Raises:
        LLMConnectionError: 無法連線、金鑰無效、位址錯誤或回應格式無法辨識。
    """
    request = _REQUEST_BUILDERS[target.provider](target)
    payload = await _get_json(request)
    try:
        return request.parse(payload)
    except ValidationError as exc:
        raise ListingNotFoundError("服務回傳的模型清單格式無法辨識，請確認 API 位址") from exc


async def _get_json(request: _ListRequest) -> object:
    host = urlparse(request.url).netloc
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(
                request.url, headers=dict(request.headers), params=dict(request.params)
            )
    except httpx.TimeoutException as exc:
        raise ServiceUnreachableError(
            f"{host} 超過 {_TIMEOUT_SECONDS} 秒沒有回應，請確認服務狀態"
        ) from exc
    except httpx.TransportError as exc:
        raise ServiceUnreachableError(f"無法連線到 {host}，請確認伺服器已啟動且位址正確") from exc

    _raise_for_status(response)
    try:
        payload: object = response.json()
    except ValueError as exc:
        raise ListingNotFoundError("服務回傳的內容不是模型清單，請確認 API 位址") from exc
    return payload


def _raise_for_status(response: httpx.Response) -> None:
    if not response.is_error:
        return
    message = _STATUS_MESSAGES.get(
        response.status_code, f"服務回應錯誤（HTTP {response.status_code}），請稍後再試"
    )
    if response.status_code == httpx.codes.NOT_FOUND:
        raise ListingNotFoundError(message)
    if response.status_code in (httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN):
        raise ListingUnauthorizedError(message)
    raise LLMConnectionError(message)


_OPENAI_COMPATIBLE_SUFFIX: Final = "/v1"


@dataclass(frozen=True)
class LocalServerListing:
    """偵測到的本地伺服器類型、實際可用的位址與模型。"""

    provider: LlmProvider
    api_base: str
    models: list[AvailableModel]


def _local_candidates(api_base: str) -> list[tuple[LlmProvider, str]]:
    if api_base.endswith(_OPENAI_COMPATIBLE_SUFFIX):
        return [(LlmProvider.OPENAI_COMPATIBLE, api_base)]
    # 使用者常只填主機與連接埠（例如 LM Studio 的 http://localhost:1234），自動補上 /v1 再試
    return [
        (LlmProvider.OLLAMA, api_base),
        (LlmProvider.OPENAI_COMPATIBLE, f"{api_base}{_OPENAI_COMPATIBLE_SUFFIX}"),
        (LlmProvider.OPENAI_COMPATIBLE, api_base),
    ]


async def detect_local_models(api_base: str, api_key: str | None) -> LocalServerListing:
    """依序嘗試 Ollama 與 OpenAI 相容的清單 API，回傳第一個成功的結果。

    連不上主機或金鑰錯誤時立即回報，不再嘗試其他路徑。

    Raises:
        LLMConnectionError: 無法連線、金鑰無效，或此位址不是支援的伺服器。
    """
    for provider, base in _local_candidates(api_base):
        target = ListingTarget(provider, api_base=base, api_key=api_key)
        try:
            models = await fetch_models(target)
        except ListingNotFoundError:
            continue
        return LocalServerListing(provider=provider, api_base=base, models=models)
    raise LLMConnectionError("此位址不是 Ollama 或 OpenAI 相容伺服器，請確認位址與連接埠")
