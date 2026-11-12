"""各服務模型清單 API 的回應格式與解析（純函式，不發出請求）。

`model_catalog` 負責組請求與錯誤處理，這裡只把回應轉成 `AvailableModel`；
服務改版時只需改這裡的格式定義。
"""

from typing import Final

from pydantic import BaseModel, Field

from app.schemas.available_model import AvailableModel

# Gemini 以支援的方法區分：能 generateContent 的才是對話模型
_GEMINI_CHAT_METHOD: Final = "generateContent"
_GEMINI_NAME_PREFIX: Final = "models/"
_CODEX_VISIBLE: Final = "list"


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


def parse_ollama(payload: object) -> list[AvailableModel]:
    """解析 Ollama `/api/tags`。"""
    tags = _OllamaTags.model_validate(payload)
    return [AvailableModel(id=model.name) for model in tags.models]


def parse_openai(payload: object) -> list[AvailableModel]:
    """解析 OpenAI 相容 `/v1/models`。"""
    listing = _OpenAIModelList.model_validate(payload)
    return [AvailableModel(id=model.id) for model in listing.data]


def parse_gemini(payload: object) -> list[AvailableModel]:
    """解析 Gemini `models`；只保留能對話（generateContent）的模型。"""
    listing = _GeminiModelList.model_validate(payload)
    return [
        AvailableModel(id=model.name.removeprefix(_GEMINI_NAME_PREFIX), label=model.display_name)
        for model in listing.models
        if _GEMINI_CHAT_METHOD in model.methods
    ]


def parse_codex(payload: object) -> list[AvailableModel]:
    """解析 ChatGPT 訂閱（Codex）`/models`；只保留帳號可選的模型。"""
    listing = _CodexModelList.model_validate(payload)
    # 依 Codex 模型選單的排序（priority 小的在前），只保留帳號可選的模型
    visible = sorted(
        (model for model in listing.models if model.visibility == _CODEX_VISIBLE),
        key=lambda model: model.priority,
    )
    return [AvailableModel(id=model.slug, label=model.display_name) for model in visible]
