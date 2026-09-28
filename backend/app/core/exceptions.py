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
