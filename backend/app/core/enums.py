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


class Verdict(StrEnum):
    """稽核判定（暫定四級，分級方式仍待決）。"""

    PASS = "PASS"  # noqa: S105 判定名稱，不是密碼
    WARNING = "WARNING"
    ERROR = "ERROR"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class Sex(StrEnum):
    """性別。"""

    M = "M"
    F = "F"


class AgeGroup(StrEnum):
    """年齡層（< 45／45–64／≥ 65），僅用於選擇病床圖片。"""

    YOUNG = "young"
    MIDDLE = "middle"
    ELDER = "elder"


class BedBoardStatus(StrEnum):
    """病床總覽上每床顯示的狀態：已稽核時為最嚴重判定，尚未稽核時為 `NOT_AUDITED`。"""

    ERROR = "ERROR"
    WARNING = "WARNING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    PASS = "PASS"  # noqa: S105 判定名稱，不是密碼
    NOT_AUDITED = "NOT_AUDITED"


class RawRecordCategory(StrEnum):
    """原始資料時間軸的紀錄類別；對應院方病人檔的各區塊。"""

    NURSING_PROGRESS_NOTE = "nursing_progress_note"
    VITAL_SIGN = "vital_sign"
    DAILY_PHYSICAL_ASSESSMENT = "daily_physical_assessment"
    ADMISSION_ASSESSMENT = "admission_assessment"
    ADMISSION_COURSE = "admission_course"
    LAB_RESULT = "lab_result"
    GCS = "gcs"
    MEDICATION_ORDER = "medication_order"
    EXAMINATION = "examination"
    CONSULTATION = "consultation"
    BED_TRANSFER = "bed_transfer"


class AbnormalFlag(StrEnum):
    """檢驗值的異常標記，由院方「異常值」欄轉換。"""

    HIGH = "high"
    LOW = "low"
    ABNORMAL = "abnormal"
    NORMAL = "normal"
