import asyncio
import json
import stat
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from litellm.llms.chatgpt.authenticator import Authenticator

from app.core.enums import ChatgptAuthState
from app.core.exceptions import ChatgptAuthRequiredError
from app.services.llm import chatgpt_auth

# chatgpt_auth 依賴的 LiteLLM 私有方法；升級 LiteLLM 後這裡失敗代表需要調整包裝
_REQUIRED_PRIVATE_METHODS = (
    "_request_device_code",
    "_poll_for_authorization_code",
    "_exchange_code_for_tokens",
    "_build_auth_record",
    "_write_auth_file",
    "_read_auth_file",
    "_refresh_tokens",
    "_is_token_expired",
    "_decode_jwt_claims",
    "get_account_id",
    "get_api_base",
)


def _write_auth_file(token_dir: Path, **fields: object) -> None:
    (token_dir / "auth.json").write_text(json.dumps(fields))


def test_litellm_authenticator_still_has_wrapped_methods() -> None:
    missing = [name for name in _REQUIRED_PRIVATE_METHODS if not hasattr(Authenticator, name)]

    assert missing == []


async def test_status_is_signed_out_without_auth_file() -> None:
    status = await chatgpt_auth.get_status()

    assert status.state == ChatgptAuthState.SIGNED_OUT


async def test_status_is_signed_in_with_refresh_token(chatgpt_token_dir: Path) -> None:
    _write_auth_file(chatgpt_token_dir, access_token="a", refresh_token="r")

    status = await chatgpt_auth.get_status()

    assert status.state == ChatgptAuthState.SIGNED_IN


async def test_sign_out_removes_auth_file(chatgpt_token_dir: Path) -> None:
    _write_auth_file(chatgpt_token_dir, access_token="a", refresh_token="r")

    status = await chatgpt_auth.sign_out()

    assert status.state == ChatgptAuthState.SIGNED_OUT
    assert not (chatgpt_token_dir / "auth.json").exists()


async def test_ensure_access_token_without_login_raises() -> None:
    with pytest.raises(ChatgptAuthRequiredError, match="尚未登入"):
        await chatgpt_auth.ensure_access_token()


async def test_ensure_access_token_returns_unexpired_credentials(chatgpt_token_dir: Path) -> None:
    _write_auth_file(
        chatgpt_token_dir,
        access_token="a",
        refresh_token="r",
        expires_at=time.time() + 3600,
        account_id="acct-test",
    )

    credentials = await chatgpt_auth.ensure_access_token()

    assert (credentials.access_token, credentials.account_id) == ("a", "acct-test")
    assert chatgpt_auth.request_headers(credentials)["ChatGPT-Account-Id"] == "acct-test"


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_configure_token_dir_restricts_permissions(chatgpt_token_dir: Path) -> None:
    chatgpt_token_dir.chmod(0o755)
    _write_auth_file(chatgpt_token_dir, access_token="a", refresh_token="r")
    (chatgpt_token_dir / "auth.json").chmod(0o644)

    chatgpt_auth.configure_token_dir(chatgpt_token_dir)

    assert _mode(chatgpt_token_dir) == 0o700
    assert _mode(chatgpt_token_dir / "auth.json") == 0o600


async def test_sign_out_during_token_write_leaves_no_auth_file(
    chatgpt_token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_started = threading.Event()
    release_write = threading.Event()
    write_done = threading.Event()
    original_write = Authenticator._write_auth_file

    def slow_write(self: Authenticator, data: Any) -> None:
        write_started.set()
        release_write.wait(timeout=5)
        original_write(self, data)
        write_done.set()

    monkeypatch.setattr(Authenticator, "_request_device_code", lambda _: {"user_code": "ABCD"})
    monkeypatch.setattr(Authenticator, "_poll_for_authorization_code", lambda _, __: {})
    monkeypatch.setattr(
        Authenticator, "_exchange_code_for_tokens", lambda _, __: {"refresh_token": "r"}
    )
    monkeypatch.setattr(Authenticator, "_build_auth_record", lambda _, tokens: dict(tokens))
    monkeypatch.setattr(Authenticator, "_write_auth_file", slow_write)

    await chatgpt_auth.start_device_login()
    await asyncio.to_thread(write_started.wait, 5)
    sign_out = asyncio.create_task(chatgpt_auth.sign_out())
    await asyncio.sleep(0.05)
    release_write.set()
    status = await sign_out
    await asyncio.to_thread(write_done.wait, 5)

    assert status.state == ChatgptAuthState.SIGNED_OUT
    assert not (chatgpt_token_dir / "auth.json").exists()


def _install_slow_refresh(
    token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[threading.Event, threading.Event]:
    """讓換發卡在執行緒中，直到測試放行；回傳（已開始、放行）兩個事件。"""
    _write_auth_file(token_dir, access_token="old", refresh_token="r", expires_at=0)
    started = threading.Event()
    release = threading.Event()

    def slow_refresh(self: Authenticator, refresh_token: str) -> dict[str, str]:
        started.set()
        release.wait(timeout=5)
        # 與 LiteLLM 相同：換發成功後重寫 token 檔
        refreshed = {"access_token": "new", "refresh_token": refresh_token}
        self._write_auth_file({**refreshed, "expires_at": time.time() + 3600})
        return refreshed

    monkeypatch.setattr(Authenticator, "_refresh_tokens", slow_refresh)
    return started, release


async def test_sign_out_during_token_refresh_leaves_no_auth_file(
    chatgpt_token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    refresh_started, release_refresh = _install_slow_refresh(chatgpt_token_dir, monkeypatch)

    refresh = asyncio.create_task(chatgpt_auth.ensure_access_token())
    await asyncio.to_thread(refresh_started.wait, 5)
    sign_out = asyncio.create_task(chatgpt_auth.sign_out())
    await asyncio.sleep(0.05)
    release_refresh.set()
    credentials = await refresh
    status = await sign_out

    assert credentials.access_token == "new"
    assert status.state == ChatgptAuthState.SIGNED_OUT
    assert not (chatgpt_token_dir / "auth.json").exists()


async def test_cancelled_refresh_keeps_lock_until_token_is_written(
    chatgpt_token_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    refresh_started, release_refresh = _install_slow_refresh(chatgpt_token_dir, monkeypatch)

    # 模擬使用者關掉頁面：請求被取消，但換發的執行緒仍在跑
    refresh = asyncio.create_task(chatgpt_auth.ensure_access_token())
    await asyncio.to_thread(refresh_started.wait, 5)
    refresh.cancel()
    with pytest.raises(asyncio.CancelledError):
        await refresh
    sign_out = asyncio.create_task(chatgpt_auth.sign_out())
    await asyncio.sleep(0.05)
    signed_out_before_refresh_finished = sign_out.done()
    release_refresh.set()
    status = await sign_out

    assert signed_out_before_refresh_finished is False
    assert status.state == ChatgptAuthState.SIGNED_OUT
    assert not (chatgpt_token_dir / "auth.json").exists()
