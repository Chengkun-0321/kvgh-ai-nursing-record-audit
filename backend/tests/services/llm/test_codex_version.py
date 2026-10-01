from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from app.core.config import get_settings
from app.services.llm import codex_version

Handler = Callable[[httpx.Request], httpx.Response]

_FALLBACK = "0.100.0"


@pytest.fixture(autouse=True)
def _fresh_cache() -> Iterator[None]:
    codex_version.reset_cache()
    yield
    codex_version.reset_cache()


def _use_settings(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> None:
    fields = {"CHATGPT_CLIENT_VERSION": None, "CHATGPT_CLIENT_VERSION_FALLBACK": _FALLBACK}
    settings = get_settings().model_copy(update=fields | overrides)
    monkeypatch.setattr(codex_version, "get_settings", lambda: settings)


def _use_transport(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    real_client = httpx.AsyncClient

    def fake_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(recording_handler), **kwargs)

    monkeypatch.setattr(codex_version.httpx, "AsyncClient", fake_client)
    return requests


async def test_configured_version_skips_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_settings(monkeypatch, CHATGPT_CLIENT_VERSION="0.150.0")
    requests = _use_transport(monkeypatch, lambda _: httpx.Response(200, json={"version": "9.9.9"}))

    assert await codex_version.resolve_client_version() == "0.150.0"
    assert requests == []


async def test_latest_version_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    _use_settings(monkeypatch)
    requests = _use_transport(
        monkeypatch, lambda _: httpx.Response(200, json={"version": "0.160.0"})
    )

    assert await codex_version.resolve_client_version() == "0.160.0"
    assert await codex_version.resolve_client_version() == "0.160.0"
    assert len(requests) == 1


def _timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectTimeout("timeout", request=request)


@pytest.mark.parametrize(
    "handler",
    [
        _timeout,
        lambda _: httpx.Response(503),
        lambda _: httpx.Response(200, text="not json"),
        lambda _: httpx.Response(200, json={"name": "@openai/codex"}),
        lambda _: httpx.Response(200, json={"version": "latest-beta"}),
    ],
    ids=["timeout", "http-error", "not-json", "missing-version", "bad-format"],
)
async def test_lookup_failure_falls_back(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> None:
    _use_settings(monkeypatch)
    requests = _use_transport(monkeypatch, handler)

    assert await codex_version.resolve_client_version() == _FALLBACK
    assert await codex_version.resolve_client_version() == _FALLBACK
    assert len(requests) == 1
