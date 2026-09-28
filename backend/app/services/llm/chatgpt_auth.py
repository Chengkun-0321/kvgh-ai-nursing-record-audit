"""ChatGPT 訂閱登入（OAuth 裝置碼流程）。

LiteLLM 內建的登入會 `print` 驗證碼並以 `time.sleep` 阻塞整個請求，無法用在網頁。
這裡重用 LiteLLM `Authenticator` 的各個步驟：取得驗證碼後立即回傳給網頁，
輪詢與換發 token 在背景執行緒完成，token 寫入 LiteLLM 讀取的同一個檔案。

依賴 LiteLLM 的私有方法（版本以 == 鎖定）；升級時由
`tests/services/llm/test_chatgpt_auth.py` 提早發現介面變動。
"""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Final

from litellm.llms.chatgpt.authenticator import (
    DEVICE_CODE_TIMEOUT_SECONDS,
    Authenticator,
    JsonObject,
)
from litellm.llms.chatgpt.common_utils import (
    CHATGPT_DEVICE_VERIFY_URL,
    GetAccessTokenError,
    GetDeviceCodeError,
    RefreshAccessTokenError,
    get_chatgpt_default_headers,
)

from app.core.enums import ChatgptAuthState
from app.core.exceptions import ChatgptAuthRequiredError, ChatgptLoginError
from app.schemas.chatgpt_auth import ChatgptAuthStatusRead

logger = logging.getLogger(__name__)

# LiteLLM 每次建立 Authenticator 都從這個環境變數決定 token 檔位置
_AUTH_DIR_ENV_VAR: Final = "CHATGPT_TOKEN_DIR"
_LOGIN_FAILED_MESSAGE: Final = "登入未完成或驗證碼已逾時，請重新登入"
# token 檔含 refresh token：只允許後端程序的擁有者讀寫
_TOKEN_DIR_MODE: Final = 0o700
_AUTH_FILE_MODE: Final = 0o600


@dataclass(frozen=True)
class _AuthSnapshot:
    is_signed_in: bool
    account_email: str | None


@dataclass
class _DeviceLogin:
    user_code: str
    expires_at: datetime
    task: asyncio.Task[None] | None = None


@dataclass
class _LoginStore:
    """進行中的登入（單一後端程序；重新啟動後需重新登入）。"""

    pending: _DeviceLogin | None = None
    last_error: str | None = None
    # 寫入 token 檔（登入完成、換發）與登出刪檔不可交錯，否則登出後 token 可能又被寫回
    auth_file_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    # 持鎖中的背景 task；保留參照，避免呼叫端取消後被回收
    exclusive_tasks: set[asyncio.Task[Any]] = field(default_factory=set)


_store = _LoginStore()


def configure_token_dir(token_dir: Path) -> None:
    """指定 token 檔目錄並限制權限（應用程式啟動時呼叫）。

    LiteLLM 也會自行建立、重寫 token 檔（依 umask 決定權限），因此以目錄權限為主要保護。
    """
    token_dir.mkdir(parents=True, exist_ok=True)
    # mkdir 的 mode 對已存在的目錄無效，一律再 chmod
    token_dir.chmod(_TOKEN_DIR_MODE)
    os.environ[_AUTH_DIR_ENV_VAR] = str(token_dir)
    _restrict_auth_file(Authenticator())


async def get_status() -> ChatgptAuthStatusRead:
    """取得目前的登入狀態。"""
    snapshot = await asyncio.to_thread(_read_auth_snapshot)
    if snapshot.is_signed_in:
        return ChatgptAuthStatusRead(
            state=ChatgptAuthState.SIGNED_IN, account_email=snapshot.account_email
        )
    pending = _store.pending
    if pending is not None:
        return ChatgptAuthStatusRead(
            state=ChatgptAuthState.PENDING,
            user_code=pending.user_code,
            verification_url=CHATGPT_DEVICE_VERIFY_URL,
            expires_at=pending.expires_at,
        )
    return ChatgptAuthStatusRead(state=ChatgptAuthState.SIGNED_OUT, error_message=_store.last_error)


async def start_device_login() -> ChatgptAuthStatusRead:
    """開始裝置碼登入；已登入或已在登入中時直接回傳目前狀態。

    Raises:
        ChatgptLoginError: 無法向 OpenAI 取得驗證碼。
    """
    status = await get_status()
    if status.state != ChatgptAuthState.SIGNED_OUT:
        return status

    authenticator = Authenticator()
    try:
        device_code = await asyncio.to_thread(authenticator._request_device_code)
    except GetDeviceCodeError as exc:
        raise ChatgptLoginError("無法向 OpenAI 取得登入驗證碼，請確認網路連線後再試") from exc
    # LiteLLM 取得驗證碼時會把冷卻時間寫進 token 檔
    await asyncio.to_thread(_restrict_auth_file, authenticator)

    login = _DeviceLogin(
        user_code=device_code["user_code"],
        expires_at=datetime.now(UTC) + timedelta(seconds=DEVICE_CODE_TIMEOUT_SECONDS),
    )
    _store.pending = login
    _store.last_error = None
    login.task = asyncio.create_task(_complete_login(authenticator, device_code, login))
    return await get_status()


async def sign_out() -> ChatgptAuthStatusRead:
    """登出：刪除 token 檔，並放棄進行中的登入。"""
    await _run_exclusively(_discard_login_and_token)
    logger.info("已登出 ChatGPT 訂閱")
    return await get_status()


async def _discard_login_and_token() -> None:
    pending = _store.pending
    _store.pending = None
    _store.last_error = None
    if pending is not None and pending.task is not None:
        pending.task.cancel()
    auth_file = Path(Authenticator().auth_file)
    await asyncio.to_thread(auth_file.unlink, missing_ok=True)


@dataclass(frozen=True)
class ChatgptCredentials:
    """呼叫 ChatGPT Codex 後端所需的憑證（只在查詢當下使用，不快取）。"""

    access_token: str
    account_id: str | None
    api_base: str


async def ensure_access_token() -> ChatgptCredentials:
    """確認有可用的 access token，過期就先換發。

    必須在呼叫 `chatgpt/` 模型前執行：沒有可用 token 時 LiteLLM 會進入阻塞式登入。

    與登出共用同一把鎖：換發會重寫 token 檔，不可與登出的刪檔交錯；
    也避免兩個請求以同一個 refresh token 同時換發（OpenAI 會輪替 refresh token，後到者會失效）。

    Raises:
        ChatgptAuthRequiredError: 尚未登入，或登入已失效。
    """
    return await _run_exclusively(lambda: asyncio.to_thread(_ensure_access_token_sync))


def request_headers(credentials: ChatgptCredentials) -> dict[str, str]:
    """與 LiteLLM 呼叫 Codex 後端時相同的標頭（originator、User-Agent、帳戶 ID）。"""
    headers: dict[str, str] = get_chatgpt_default_headers(
        credentials.access_token, credentials.account_id
    )
    headers["accept"] = "application/json"
    return headers


def _ensure_access_token_sync() -> ChatgptCredentials:
    authenticator = Authenticator()
    auth_data = authenticator._read_auth_file()
    refresh_token = auth_data.get("refresh_token") if auth_data else None
    if auth_data is None or not isinstance(refresh_token, str):
        raise ChatgptAuthRequiredError("尚未登入 ChatGPT 帳號，請先在「ChatGPT 帳號」區塊登入")

    access_token = auth_data.get("access_token")
    if not isinstance(access_token, str) or authenticator._is_token_expired(
        auth_data, access_token
    ):
        access_token = _refresh_access_token(authenticator, refresh_token)
    return ChatgptCredentials(
        access_token=access_token,
        account_id=authenticator.get_account_id(),
        api_base=authenticator.get_api_base(),
    )


def _refresh_access_token(authenticator: Authenticator, refresh_token: str) -> str:
    try:
        tokens = authenticator._refresh_tokens(refresh_token)
    except RefreshAccessTokenError as exc:
        raise ChatgptAuthRequiredError("ChatGPT 登入已失效，請重新登入") from exc
    _restrict_auth_file(authenticator)
    return tokens["access_token"]


async def _complete_login(
    authenticator: Authenticator, device_code: dict[str, str], login: _DeviceLogin
) -> None:
    try:
        authorization = await asyncio.to_thread(
            authenticator._poll_for_authorization_code, device_code
        )
        tokens = await asyncio.to_thread(authenticator._exchange_code_for_tokens, authorization)
    except GetAccessTokenError as exc:
        logger.warning("ChatGPT 裝置碼登入失敗：%s", type(exc).__name__)
        _finish_login(login, error_message=_LOGIN_FAILED_MESSAGE)
        return

    await _run_exclusively(lambda: _save_login_tokens(authenticator, tokens, login))


async def _save_login_tokens(
    authenticator: Authenticator, tokens: dict[str, str], login: _DeviceLogin
) -> None:
    # 使用者已登出或重新開始登入時，捨棄這次取得的 token
    if _store.pending is login:
        record = authenticator._build_auth_record(tokens)
        await asyncio.to_thread(_write_auth_record, authenticator, record)
        logger.info("ChatGPT 訂閱登入完成")
    _finish_login(login, error_message=None)


async def _run_exclusively[T](operation: Callable[[], Awaitable[T]]) -> T:
    """持憑證檔鎖執行操作；呼叫端被取消時，操作仍在背景跑完才釋放鎖。

    檔案操作在執行緒中進行，取消無法中止執行緒；若隨呼叫端一起釋放鎖，
    登出可能先刪檔、仍在跑的換發再把 token 寫回。
    """

    async def locked() -> T:
        async with _store.auth_file_lock:
            return await operation()

    task = asyncio.create_task(locked())
    _store.exclusive_tasks.add(task)
    task.add_done_callback(_store.exclusive_tasks.discard)
    return await asyncio.shield(task)


def _write_auth_record(authenticator: Authenticator, record: JsonObject) -> None:
    authenticator._write_auth_file(record)
    _restrict_auth_file(authenticator)


def _restrict_auth_file(authenticator: Authenticator) -> None:
    auth_file = Path(authenticator.auth_file)
    if auth_file.exists():
        auth_file.chmod(_AUTH_FILE_MODE)


def _finish_login(login: _DeviceLogin, *, error_message: str | None) -> None:
    if _store.pending is login:
        _store.pending = None
        _store.last_error = error_message


def _read_auth_snapshot() -> _AuthSnapshot:
    authenticator = Authenticator()
    auth_data = authenticator._read_auth_file()
    if auth_data is None or not isinstance(auth_data.get("refresh_token"), str):
        return _AuthSnapshot(is_signed_in=False, account_email=None)
    id_token = auth_data.get("id_token")
    claims = authenticator._decode_jwt_claims(id_token) if isinstance(id_token, str) else {}
    email = claims.get("email")
    return _AuthSnapshot(is_signed_in=True, account_email=email if isinstance(email, str) else None)
