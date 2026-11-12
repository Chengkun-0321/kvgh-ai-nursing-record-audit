"""模型服務錯誤 → 繁中可操作訊息。

本模組不 import litellm（llm.md：只有 gateway 可 import）：LiteLLM 的例外類別由 gateway
組成 `ErrorCatalog` 傳入，這裡只負責比對規則與組出訊息。不回傳原始例外字串，只附遮蔽後的服務說明。
"""

from collections.abc import Callable
from dataclasses import dataclass

from app.services.llm.config_service import StoredLlmConfig
from app.services.llm.providers import resolve_api_base
from app.services.llm.redaction import redact_provider_detail


@dataclass(frozen=True)
class ErrorRule:
    """一種例外對應的訊息；`matches` 用來再細分同一類別（如被包裝的連線錯誤）。"""

    error_type: type[Exception]
    describe: Callable[[StoredLlmConfig], str]
    matches: Callable[[Exception], bool] = lambda _: True


@dataclass(frozen=True)
class ErrorCatalog:
    """例外對照表。

    Attributes:
        rules: 依序比對，第一個符合的決定訊息；子類別必須排在父類別前面。
        bad_request_type: 都不符合時，此類別（及子類別）視為「服務拒絕此請求」，其餘為「回應錯誤」。
    """

    rules: tuple[ErrorRule, ...]
    bad_request_type: type[Exception]


def describe_invalid_api_key(_: StoredLlmConfig) -> str:
    """金鑰無效（AuthenticationError）。"""
    return "API 金鑰無效或已過期，請確認金鑰"


def describe_permission_denied(_: StoredLlmConfig) -> str:
    """金鑰沒有該模型的權限（PermissionDeniedError）。"""
    return "此金鑰沒有使用該模型的權限，請確認帳戶或專案設定"


def describe_model_not_found(config: StoredLlmConfig) -> str:
    """找不到模型（NotFoundError）。"""
    return f"找不到模型「{config.model}」，請確認模型名稱"


def describe_rate_limited(_: StoredLlmConfig) -> str:
    """速率或額度上限（RateLimitError）。"""
    return "已達服務的速率或額度上限，請稍後再試或確認帳戶額度"


def describe_timeout(config: StoredLlmConfig) -> str:
    """逾時（Timeout）。"""
    return f"超過 {config.timeout_seconds} 秒沒有回應，請確認服務狀態或調高逾時秒數"


def describe_connection_failure(config: StoredLlmConfig) -> str:
    """無法連線；指出實際連線的位址，方便確認本地伺服器。"""
    target = resolve_api_base(config.provider, config.api_base) or "模型服務"
    return f"無法連線到 {target}，請確認伺服器已啟動且位址正確"


def describe_context_window_exceeded(_: StoredLlmConfig) -> str:
    """對話超過模型長度上限（ContextWindowExceededError）。"""
    return "對話內容超過模型可處理的長度，請清除對話後再試"


def describe_service_unavailable(_: StoredLlmConfig) -> str:
    """服務暫停（ServiceUnavailableError）。"""
    return "模型服務暫時無法使用，請稍後再試"


def is_wrapped_connection_error(exc: Exception) -> bool:
    """LiteLLM 的 openai 路徑把連線失敗包成 InternalServerError（訊息為 "Connection error."）。"""
    return "connection error" in str(getattr(exc, "message", "")).lower()


def describe_error(
    exc: Exception, catalog: ErrorCatalog, config: StoredLlmConfig, api_key: str | None
) -> str:
    """把模型服務的例外轉成可操作的繁中訊息。

    Args:
        exc: LiteLLM 拋出的例外。
        catalog: gateway 提供的例外對照表。
        config: 這次呼叫的模型設定（訊息會帶模型名稱、位址、逾時秒數）。
        api_key: 這次呼叫的明文金鑰；只用來從服務說明中遮蔽，不會出現在訊息裡。

    Returns:
        繁中訊息；不含原始例外字串，服務說明經遮蔽後才附上。
    """
    for rule in catalog.rules:
        if isinstance(exc, rule.error_type) and rule.matches(exc):
            return rule.describe(config)
    detail = redact_provider_detail(str(getattr(exc, "message", "") or ""), api_key)
    base = "服務拒絕此請求，請確認模型名稱與設定"
    if not isinstance(exc, catalog.bad_request_type):
        base = "模型服務回應錯誤，請稍後再試"
    return f"{base}（{detail}）" if detail else base
