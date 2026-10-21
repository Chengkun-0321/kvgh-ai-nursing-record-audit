"""應用程式例外階層：由 `main.py` 的 exception handler 統一轉為 HTTP 回應。

訊息會直接顯示給使用者，必須是繁中、可操作，且不得含 API key 或病患識別資料。
"""


class AppError(Exception):
    """所有應用程式例外的基底。"""

    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """查無資料。"""

    status_code = 404


class ConflictError(AppError):
    """與目前狀態衝突（名稱重複、刪除使用中的設定…）。"""

    status_code = 409


class InvalidInputError(AppError):
    """輸入欄位組合不符規則（例如該服務類型必填 API 金鑰）。"""

    status_code = 422


class SecretDecryptError(AppError):
    """已儲存的 API 金鑰無法解密（加密金鑰變更或資料損毀）。"""

    status_code = 500


class LLMConnectionError(AppError):
    """呼叫模型服務失敗（金鑰無效、找不到模型、連線失敗、逾時…）。"""

    status_code = 502


class ChatgptAuthRequiredError(ConflictError):
    """ChatGPT 訂閱尚未登入或登入已失效。"""


class ChatgptLoginError(AppError):
    """無法向 OpenAI 取得登入裝置碼。"""

    status_code = 502


class PatientNotFoundError(NotFoundError):
    """病患沒有出現在任何可解析的資料包清單（E1）。"""

    def __init__(self, message: str = "找不到此病患的資料") -> None:
        super().__init__(message)


class BusinessDateNotFoundError(NotFoundError):
    """該日期不是此病患有資料的業務日期（E2）。"""

    def __init__(self, message: str = "此日期沒有該病患的資料") -> None:
        super().__init__(message)


class NotAuditableError(InvalidInputError):
    """入院首日沒有前日紀錄可比較，不可稽核（E4）。"""

    def __init__(self, message: str = "入院首日無前日紀錄可比較") -> None:
        super().__init__(message)


class LLMNotConfiguredError(ConflictError):
    """尚未設定使用中的模型（E5）。"""

    def __init__(self, message: str = "尚未設定使用中的模型，請至設定頁設定") -> None:
        super().__init__(message)


class LLMOutputError(AppError):
    """模型輸出不符 schema，重試用盡仍失敗；訊息不含模型原文。"""

    status_code = 502

    def __init__(self, message: str = "模型輸出格式不符，無法完成判定") -> None:
        super().__init__(message)


class LLMTimeoutError(TimeoutError):
    """呼叫模型逾時；繼承 `TimeoutError`，gateway 以外不必 import litellm 也能辨識。"""


class LLMServiceError(ConnectionError):
    """呼叫模型服務失敗（連線失敗、服務錯誤）；繼承 `ConnectionError`，gateway 以外也能辨識。"""
