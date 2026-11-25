"""Demo 登入：固定帳密比對、簽發與驗證 session token。

token 格式為 `<base64url(帳號)>.<到期 epoch 秒>.<base64url(HMAC-SHA256 簽章)>`，
存在 HttpOnly cookie；後端不保存 session，驗證只靠簽章與到期時間。
帳密、token 都不得寫入 log 或例外訊息。
"""

import base64
import binascii
import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Final

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError

SESSION_COOKIE_NAME: Final = "kvgh_session"
INVALID_CREDENTIALS_MESSAGE: Final = "帳號或密碼錯誤"
LOGIN_REQUIRED_MESSAGE: Final = "請先登入"

# 簽章金鑰由既有的加密金鑰衍生，加上用途字串與 API key 加密分開；改版格式時換版本號
_SIGNING_KEY_PURPOSE: Final = b"kvgh-session-v1"
_FIELD_SEPARATOR: Final = "."
_FIELD_COUNT: Final = 3


@dataclass(frozen=True)
class IssuedSession:
    """登入成功後要寫入 cookie 的 session。"""

    username: str
    token: str
    max_age_seconds: int


def login(username: str, password: str) -> IssuedSession:
    """比對 demo 帳密，成功時簽發 session token。

    Args:
        username: 使用者輸入的帳號。
        password: 使用者輸入的密碼。

    Returns:
        帳號、token 與 cookie 有效秒數。

    Raises:
        AuthenticationError: 帳號或密碼錯誤（不區分是哪一項錯，避免洩漏帳號是否存在）。
    """
    if not _matches_demo_credentials(username, password):
        raise AuthenticationError(INVALID_CREDENTIALS_MESSAGE)
    settings = get_settings()
    return IssuedSession(
        username=settings.DEMO_LOGIN_USERNAME,
        token=create_session_token(settings.DEMO_LOGIN_USERNAME, int(time.time())),
        max_age_seconds=settings.SESSION_MAX_AGE_SECONDS,
    )


def create_session_token(username: str, issued_at: int) -> str:
    """簽發 session token。

    Args:
        username: 登入的帳號。
        issued_at: 簽發時間（epoch 秒）；到期時間為此值加 `SESSION_MAX_AGE_SECONDS`。

    Returns:
        `<帳號>.<到期時間>.<簽章>` 格式的 token。
    """
    expires_at = issued_at + get_settings().SESSION_MAX_AGE_SECONDS
    payload = f"{_b64encode(username.encode())}{_FIELD_SEPARATOR}{expires_at}"
    return f"{payload}{_FIELD_SEPARATOR}{_sign(payload)}"


def verify_session_token(token: str | None, now: int | None = None) -> str:
    """驗證 session token：格式、簽章、到期時間、帳號皆須通過。

    Args:
        token: cookie 內的 token；未登入時為 None。
        now: 目前時間（epoch 秒）；None 時取系統時間，測試可指定。

    Returns:
        已登入的帳號。

    Raises:
        AuthenticationError: 未登入、token 格式不符、簽章不符、已過期或帳號已變更。
    """
    parts = token.split(_FIELD_SEPARATOR) if token else []
    if len(parts) != _FIELD_COUNT:
        raise AuthenticationError(LOGIN_REQUIRED_MESSAGE)
    encoded_username, expires_text, signature = parts
    payload = f"{encoded_username}{_FIELD_SEPARATOR}{expires_text}"
    if not hmac.compare_digest(signature.encode(), _sign(payload).encode()):
        raise AuthenticationError(LOGIN_REQUIRED_MESSAGE)
    current_time = int(time.time()) if now is None else now
    if not expires_text.isdigit() or int(expires_text) <= current_time:
        raise AuthenticationError(LOGIN_REQUIRED_MESSAGE)
    username = _decode_username(encoded_username)
    if not _is_same_text(username, get_settings().DEMO_LOGIN_USERNAME):
        raise AuthenticationError(LOGIN_REQUIRED_MESSAGE)
    return username


def _matches_demo_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    # 兩項都比對完才判斷，不因帳號錯就提早回傳，避免以回應時間推測帳號
    is_username_match = _is_same_text(username, settings.DEMO_LOGIN_USERNAME)
    is_password_match = _is_same_text(password, settings.DEMO_LOGIN_PASSWORD.get_secret_value())
    return is_username_match and is_password_match


def _is_same_text(given: str, expected: str) -> bool:
    # compare_digest 對 str 只接受 ASCII，先轉 UTF-8 bytes 才能比對中文帳密
    return hmac.compare_digest(given.encode(), expected.encode())


def _sign(payload: str) -> str:
    digest = hmac.new(_signing_key(), payload.encode(), hashlib.sha256).digest()
    return _b64encode(digest)


def _signing_key() -> bytes:
    secret = get_settings().LLM_KEY_ENCRYPTION_KEY.get_secret_value().encode()
    return hmac.new(secret, _SIGNING_KEY_PURPOSE, hashlib.sha256).digest()


def _b64encode(raw: bytes) -> str:
    # 去掉 padding 的 base64url，cookie 值不需跳脫
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _decode_username(encoded: str) -> str:
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode()).decode()
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise AuthenticationError(LOGIN_REQUIRED_MESSAGE) from exc
