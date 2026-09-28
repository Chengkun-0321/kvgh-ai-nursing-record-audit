"""查詢可用模型的請求與回應。"""

import uuid

from pydantic import BaseModel

from app.core.enums import LlmProvider
from app.schemas.llm_config import OptionalApiBase, OptionalApiKey


class AvailableModelsQuery(BaseModel):
    """以表單目前的連線資訊查詢可用模型（新增時設定尚未儲存）。

    API 金鑰放在 body，不放 URL；編輯已儲存的設定時可只帶 `config_id`，沿用已儲存的金鑰。
    """

    provider: LlmProvider
    api_base: OptionalApiBase = None
    api_key: OptionalApiKey = None
    config_id: uuid.UUID | None = None


class AvailableModel(BaseModel):
    """一個可選的模型；`id` 即設定要儲存的模型名稱（不含 LiteLLM 前綴）。"""

    id: str
    label: str | None = None


class AvailableModelsRead(BaseModel):
    """可用模型清單。"""

    models: list[AvailableModel]


class LocalModelsQuery(BaseModel):
    """本地模型：只給伺服器位址，由後端判斷是 Ollama 還是 OpenAI 相容伺服器。"""

    # 未填時使用 Ollama 預設位址
    api_base: OptionalApiBase = None
    api_key: OptionalApiKey = None
    config_id: uuid.UUID | None = None


class LocalModelsRead(AvailableModelsRead):
    """本地伺服器的偵測結果與可用模型。"""

    # 偵測到的伺服器類型：ollama 或 openai_compatible
    provider: LlmProvider
    # 實際可用的位址（例如自動補上 /v1）
    api_base: str
