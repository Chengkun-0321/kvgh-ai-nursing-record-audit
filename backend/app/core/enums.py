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


class Verdict(StrEnum):
    """稽核判定（暫定四級，分級方式仍待決）。"""

    PASS = "PASS"  # noqa: S105  稽核判定值，非密碼；未發現問題
    WARNING = "WARNING"  # 疑似缺漏／不一致，需人工確認
    ERROR = "ERROR"  # 依明確規則可確認缺漏
    NEEDS_REVIEW = "NEEDS_REVIEW"  # 系統無法判定（資料不足、LLM 失敗）


class Engine(StrEnum):
    """判定引擎。"""

    RULE = "rule"
    LLM = "llm"
    HYBRID = "hybrid"


class IngestionStatus(StrEnum):
    """匯入批次狀態。"""

    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"


class RecordSource(StrEnum):
    """Evidence 與 prompt 中的資料來源名稱（依 glossary）。"""

    NURSING_PROGRESS_NOTE = "nursing_progress_note"
    VITAL_SIGN = "vital_sign"
    LAB_RESULT = "lab_result"
    TUBE = "tube"
