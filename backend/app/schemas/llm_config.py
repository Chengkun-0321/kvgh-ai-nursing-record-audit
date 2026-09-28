"""LLM 模型設定的輸入與輸出結構。

各服務類型的必填欄位（API 金鑰、API 位址）依合併後的狀態判斷，由 service 驗證。
"""

import uuid
from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse

from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    computed_field,
)

from app.core.constants import (
    LLM_API_BASE_MAX_LENGTH,
    LLM_API_KEY_MAX_LENGTH,
    LLM_CONFIG_NAME_MAX_LENGTH,
    LLM_MODEL_MAX_LENGTH,
    LLM_TIMEOUT_MAX_SECONDS,
    LLM_TIMEOUT_MIN_SECONDS,
)
from app.core.enums import LlmProvider

_ALLOWED_URL_SCHEMES = ("http", "https")


def _blank_to_none(value: object) -> object:
    """表單留空的欄位視為未填。"""
    if isinstance(value, str) and not value.strip():
        return None
    return value


def _normalize_api_base(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in _ALLOWED_URL_SCHEMES or not parsed.netloc:
        raise ValueError("API 位址必須以 http:// 或 https:// 開頭")
    # 結尾斜線會讓 LiteLLM 組出 `//api/chat` 之類的路徑
    return value.rstrip("/")


ConfigName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=LLM_CONFIG_NAME_MAX_LENGTH),
]
ModelName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LLM_MODEL_MAX_LENGTH)
]
ApiBase = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=LLM_API_BASE_MAX_LENGTH),
    AfterValidator(_normalize_api_base),
]
ApiKey = Annotated[SecretStr, Field(max_length=LLM_API_KEY_MAX_LENGTH)]
TimeoutSeconds = Annotated[int, Field(ge=LLM_TIMEOUT_MIN_SECONDS, le=LLM_TIMEOUT_MAX_SECONDS)]
OptionalApiBase = Annotated[ApiBase | None, BeforeValidator(_blank_to_none)]
OptionalApiKey = Annotated[ApiKey | None, BeforeValidator(_blank_to_none)]


class LlmConfigCreate(BaseModel):
    """新增模型設定。"""

    name: ConfigName
    provider: LlmProvider
    model: ModelName
    api_base: OptionalApiBase = None
    api_key: OptionalApiKey = None
    # 未填時使用 Settings.LLM_DEFAULT_TIMEOUT_SECONDS
    timeout_seconds: TimeoutSeconds | None = None


class LlmConfigUpdate(BaseModel):
    """部分更新模型設定；未傳的欄位不變更，`api_key` 留空表示沿用已儲存的金鑰。"""

    name: ConfigName | None = None
    provider: LlmProvider | None = None
    model: ModelName | None = None
    # 明確傳 null 表示清除
    api_base: OptionalApiBase = None
    api_key: OptionalApiKey = None
    clear_api_key: bool = False
    timeout_seconds: TimeoutSeconds | None = None


class LlmConfigRead(BaseModel):
    """回傳前端的模型設定；API 金鑰只給遮罩值。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    provider: LlmProvider
    model: str
    api_base: str | None
    api_key_hint: str | None
    timeout_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]  # pydantic 官方寫法
    @property
    def has_api_key(self) -> bool:
        """是否已儲存 API 金鑰。"""
        return self.api_key_hint is not None
