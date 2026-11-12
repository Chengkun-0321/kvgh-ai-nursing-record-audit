"""測試對話 endpoint：用戶端斷線時，上游模型串流要在請求結束前關閉，不依賴垃圾回收。

httpx 的 ASGITransport 會先讀完整個回應，無法模擬中途斷線，因此直接以 ASGI 介面呼叫 app。
"""

import asyncio
import contextlib
import json
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from starlette.requests import ClientDisconnect

from app.main import app
from app.services.llm import gateway

_BASE = "/api/v1/llm-configs"
_CHAT_BODY = json.dumps({"messages": [{"role": "user", "content": "你好"}]}).encode()
# 上游一口氣送出的 chunk 數：遠多於 SSE 的緩衝，斷線時 relay 必定停在 yield
_UPSTREAM_CHUNKS = 1000


class _FastUpstream:
    """不等待就連續產生 chunk 的上游；記錄是否被關閉。"""

    def __init__(self) -> None:
        self.remaining = _UPSTREAM_CHUNKS
        self.closed = False

    def __aiter__(self) -> "_FastUpstream":
        return self

    async def __anext__(self) -> SimpleNamespace:
        if self.remaining == 0:
            raise StopAsyncIteration
        self.remaining -= 1
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="字"))])

    async def aclose(self) -> None:
        self.closed = True


class _DisconnectingClient:
    """收到第一段 SSE 內容後就斷線的用戶端。

    uvicorn 的 `spec_version` 為 2.3：Starlette 另開 task 等待 receive 回傳 `http.disconnect`；
    2.4 以上則以 send 拋出 OSError 判斷斷線。兩種都測。
    """

    def __init__(self, spec_version: str) -> None:
        self.spec_version = spec_version
        self.is_send_raising = spec_version == "2.4"
        self.has_received_body = False
        self._is_request_sent = False
        self._body_received = asyncio.Event()

    def build_scope(self, path: str) -> dict[str, Any]:
        return {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": self.spec_version},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"test"), (b"content-type", b"application/json")],
            "client": ("127.0.0.1", 50000),
            "server": ("test", 80),
        }

    async def receive(self) -> dict[str, Any]:
        if not self._is_request_sent:
            self._is_request_sent = True
            return {"type": "http.request", "body": _CHAT_BODY, "more_body": False}
        await self._body_received.wait()
        return {"type": "http.disconnect"}

    async def send(self, message: dict[str, Any]) -> None:
        if message["type"] != "http.response.body" or not message.get("body"):
            return
        if self.has_received_body and self.is_send_raising:
            raise OSError("用戶端已斷線")
        self.has_received_body = True
        self._body_received.set()


async def _create_config(client: AsyncClient) -> str:
    payload = {"name": "本地 Ollama", "provider": "ollama", "model": "llama3.2"}
    response = await client.post(_BASE, json=payload)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _install_upstream(monkeypatch: pytest.MonkeyPatch) -> _FastUpstream:
    upstream = _FastUpstream()

    async def fake_acompletion(**_: Any) -> _FastUpstream:
        return upstream

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)
    return upstream


async def _call_app(client: _DisconnectingClient, path: str) -> None:
    # spec 2.4 的斷線以例外結束請求（FastAPI 的 SSE task group 會包成 ExceptionGroup），屬預期；
    # Python 3.12 起 suppress 也能從 ExceptionGroup 中排除指定例外
    with contextlib.suppress(ClientDisconnect):
        await app(client.build_scope(path), client.receive, client.send)


@pytest.mark.parametrize("spec_version", ["2.3", "2.4"])
async def test_client_disconnect_closes_upstream_before_request_ends(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, spec_version: str
) -> None:
    config_id = await _create_config(client)
    upstream = _install_upstream(monkeypatch)
    disconnecting = _DisconnectingClient(spec_version)

    await _call_app(disconnecting, f"{_BASE}/{config_id}/chat")

    # 請求一結束就檢查，中間不讓出事件迴圈：GC 觸發的 aclose 還來不及執行
    assert disconnecting.has_received_body is True
    assert upstream.remaining > 0
    assert upstream.closed is True
