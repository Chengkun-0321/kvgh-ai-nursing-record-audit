"""測試用的 demo 登入帳密（虛構）與登入輔助函式。"""

from httpx import AsyncClient

TEST_USERNAME = "demo-tester"
TEST_PASSWORD = "test-password-123"


async def sign_in(http: AsyncClient) -> None:
    """以測試帳密登入，之後的請求會自動帶上 session cookie。"""
    response = await http.post(
        "/api/v1/auth/login", json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
