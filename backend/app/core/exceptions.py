"""應用程式例外階層：由 `main.py` 的 exception handler 統一轉為 HTTP 回應。

訊息會直接顯示給使用者，必須是繁中、可操作，且不得含 API key 或病患識別資料。
"""


class AppError(Exception):
    """所有應用程式例外的基底。"""

    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthenticationError(AppError):
    """未登入、登入已失效，或帳號密碼錯誤。"""

    status_code = 401


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


class LLMNotConfiguredError(ConflictError):
    """沒有使用中的模型設定，無法執行需要 LLM 的稽核。"""


class DayNotEndedError(ConflictError):
    """所選稽核日尚未結束（今天或之後），不可稽核。"""


class AuditAlreadyRunningError(ConflictError):
    """同一項稽核（病人＋規則＋稽核日）正在執行中，不重複執行。"""


class LLMOutputError(AppError):
    """模型輸出經重試後仍不符合要求的格式；稽核規則會轉為 NEEDS_REVIEW，不視為 PASS。"""

    status_code = 502


class ChatgptAuthRequiredError(ConflictError):
    """ChatGPT 訂閱尚未登入或登入已失效。"""


class ChatgptLoginError(AppError):
    """無法向 OpenAI 取得登入裝置碼。"""

    status_code = 502


class HospitalDataError(AppError):
    """院方資料檔無法讀取或格式不符，需檢查資料來源。"""

    status_code = 500
