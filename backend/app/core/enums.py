"""列舉只在此定義一次，models 與 schemas 共用。"""

from enum import StrEnum


class LlmProvider(StrEnum):
    """模型服務類型；對應的 LiteLLM 前綴與必填欄位見 `services/llm/providers.py`。"""

    OPENAI = "openai"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


class FieldRequirement(StrEnum):
    """設定欄位在該服務類型是否需要。"""

    REQUIRED = "required"
    OPTIONAL = "optional"
    UNUSED = "unused"


class ProviderChoice(StrEnum):
    """畫面上的服務類型選項；Ollama 與 OpenAI 相容伺服器合併為「本地模型」。"""

    OPENAI = "openai"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    LOCAL = "local"


class WizardStepId(StrEnum):
    """設定精靈的步驟。"""

    PROVIDER = "provider"
    CONNECTION = "connection"
    MODEL = "model"
    DETAILS = "details"


class DraftField(StrEnum):
    """設定精靈中會被檢查的欄位。"""

    API_BASE = "api_base"
    API_KEY = "api_key"
    MODEL = "model"
    NAME = "name"
    TIMEOUT_SECONDS = "timeout_seconds"


class ModelListPlanKind(StrEnum):
    """查詢可用模型的方式；`blocked` 表示缺少必要資訊，前端不發出請求。"""

    LOCAL = "local"
    REMOTE = "remote"
    BLOCKED = "blocked"


class SettingChangeAction(StrEnum):
    """設定變更紀錄的操作類型。"""

    CREATE = "create"
    UPDATE = "update"
    ACTIVATE = "activate"
    DELETE = "delete"


class ChatRole(StrEnum):
    """測試對話的訊息角色。"""

    USER = "user"
    ASSISTANT = "assistant"


class ChatgptAuthState(StrEnum):
    """ChatGPT 訂閱登入狀態。"""

    SIGNED_OUT = "signed_out"
    PENDING = "pending"
    SIGNED_IN = "signed_in"
