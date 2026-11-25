"""Demo 登入 token 的簽發與驗證（不經 HTTP）。"""

import pytest

from app.core.exceptions import AuthenticationError
from app.services import auth
from tests.auth_helpers import TEST_PASSWORD, TEST_USERNAME

ISSUED_AT = 1_800_000_000
MAX_AGE_SECONDS = 43200


def test_token_is_valid_until_expiry() -> None:
    token = auth.create_session_token(TEST_USERNAME, ISSUED_AT)

    assert auth.verify_session_token(token, now=ISSUED_AT + MAX_AGE_SECONDS - 1) == TEST_USERNAME


def test_token_at_expiry_is_rejected() -> None:
    token = auth.create_session_token(TEST_USERNAME, ISSUED_AT)

    with pytest.raises(AuthenticationError, match="請先登入"):
        auth.verify_session_token(token, now=ISSUED_AT + MAX_AGE_SECONDS)


def test_token_with_extended_expiry_is_rejected() -> None:
    encoded_username, expires_at, signature = auth.create_session_token(
        TEST_USERNAME, ISSUED_AT
    ).split(".")

    with pytest.raises(AuthenticationError):
        auth.verify_session_token(
            f"{encoded_username}.{int(expires_at) + 1}.{signature}", now=ISSUED_AT
        )


def test_missing_token_is_rejected() -> None:
    with pytest.raises(AuthenticationError, match="請先登入"):
        auth.verify_session_token(None)


def test_token_for_other_username_is_rejected() -> None:
    # 簽章正確但帳號已不是目前設定的帳號（例如設定已更換）
    token = auth.create_session_token("old-account", ISSUED_AT)

    with pytest.raises(AuthenticationError):
        auth.verify_session_token(token, now=ISSUED_AT)


def test_login_returns_token_that_verifies() -> None:
    session = auth.login(TEST_USERNAME, TEST_PASSWORD)

    assert session.username == TEST_USERNAME
    assert session.max_age_seconds == MAX_AGE_SECONDS
    assert auth.verify_session_token(session.token) == TEST_USERNAME
    assert TEST_PASSWORD not in session.token


def test_login_with_non_ascii_wrong_password_raises_auth_error() -> None:
    with pytest.raises(AuthenticationError, match="帳號或密碼錯誤"):
        auth.login(TEST_USERNAME, "錯誤密碼")
