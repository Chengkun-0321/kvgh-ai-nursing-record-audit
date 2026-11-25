"""Demo 登入 API：登入、登出、session 查詢，以及受保護 API 的 401。"""

import time

import pytest
from httpx import AsyncClient

from app.services import auth
from tests.auth_helpers import TEST_PASSWORD, TEST_USERNAME

LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
SESSION = "/api/v1/auth/session"
PROTECTED = "/api/v1/wards"


async def test_login_success_returns_username_and_httponly_cookie(
    anonymous_client: AsyncClient,
) -> None:
    response = await anonymous_client.post(
        LOGIN, json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    assert response.json() == {"username": TEST_USERNAME}
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f"{auth.SESSION_COOKIE_NAME}=")
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    assert "Max-Age=43200" in set_cookie
    assert "Secure" not in set_cookie


@pytest.mark.parametrize(
    ("username", "password"),
    [("someone-else", TEST_PASSWORD), (TEST_USERNAME, "wrong-password")],
    ids=["wrong_username", "wrong_password"],
)
async def test_login_with_wrong_credentials_returns_401(
    anonymous_client: AsyncClient, username: str, password: str
) -> None:
    response = await anonymous_client.post(LOGIN, json={"username": username, "password": password})

    assert response.status_code == 401
    assert response.json() == {"detail": "帳號或密碼錯誤"}
    assert "set-cookie" not in response.headers


async def test_protected_api_without_login_returns_401(anonymous_client: AsyncClient) -> None:
    response = await anonymous_client.get(PROTECTED)

    assert response.status_code == 401
    assert response.json() == {"detail": "請先登入"}


async def test_protected_api_after_login_succeeds(client: AsyncClient) -> None:
    response = await client.get(PROTECTED)

    assert response.status_code == 200


async def test_session_when_logged_in_returns_username(client: AsyncClient) -> None:
    response = await client.get(SESSION)

    assert response.status_code == 200
    assert response.json() == {"username": TEST_USERNAME}


async def test_session_when_not_logged_in_returns_401(anonymous_client: AsyncClient) -> None:
    response = await anonymous_client.get(SESSION)

    assert response.status_code == 401
    assert response.json() == {"detail": "請先登入"}


async def test_tampered_signature_returns_401(anonymous_client: AsyncClient) -> None:
    token = auth.create_session_token(TEST_USERNAME, int(time.time()))
    payload, _, signature = token.rpartition(".")
    tampered = f"{payload}.{'A' if signature[0] != 'A' else 'B'}{signature[1:]}"
    anonymous_client.cookies.set(auth.SESSION_COOKIE_NAME, tampered)

    response = await anonymous_client.get(SESSION)

    assert response.status_code == 401


async def test_token_with_forged_username_returns_401(anonymous_client: AsyncClient) -> None:
    token = auth.create_session_token(TEST_USERNAME, int(time.time()))
    _, expires_at, signature = token.split(".")
    forged_username = auth.create_session_token("intruder", 0).split(".")[0]
    anonymous_client.cookies.set(
        auth.SESSION_COOKIE_NAME, f"{forged_username}.{expires_at}.{signature}"
    )

    response = await anonymous_client.get(PROTECTED)

    assert response.status_code == 401


async def test_expired_token_returns_401(anonymous_client: AsyncClient) -> None:
    long_ago = int(time.time()) - 2 * 43200
    anonymous_client.cookies.set(
        auth.SESSION_COOKIE_NAME, auth.create_session_token(TEST_USERNAME, long_ago)
    )

    response = await anonymous_client.get(SESSION)

    assert response.status_code == 401
    assert response.json() == {"detail": "請先登入"}


@pytest.mark.parametrize("token", ["garbage", "a.b", "a.b.c.d", "...", ""])
async def test_malformed_token_returns_401(anonymous_client: AsyncClient, token: str) -> None:
    anonymous_client.cookies.set(auth.SESSION_COOKIE_NAME, token)

    response = await anonymous_client.get(PROTECTED)

    assert response.status_code == 401


async def test_logout_clears_cookie_and_blocks_protected_api(client: AsyncClient) -> None:
    response = await client.post(LOGOUT)

    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert set_cookie.startswith(f'{auth.SESSION_COOKIE_NAME}=""')
    assert "Max-Age=0" in set_cookie
    assert auth.SESSION_COOKIE_NAME not in client.cookies
    assert (await client.get(PROTECTED)).status_code == 401


async def test_logout_without_login_returns_204(anonymous_client: AsyncClient) -> None:
    response = await anonymous_client.post(LOGOUT)

    assert response.status_code == 204
