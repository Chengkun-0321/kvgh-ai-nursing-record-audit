"""列舉只在此定義一次，models 與 schemas 共用。"""

from enum import StrEnum


class LlmProvider(StrEnum):
    """模型服務類型；對應的 LiteLLM 前綴與必填欄位見 `services/llm/providers.py`。"""

    OPENAI = "openai"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    OPENAI_COMPATIBLE = "openai_compatible"


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
