from collections.abc import Callable
from typing import Any

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import LlmProvider
from app.core.exceptions import ChatgptAuthRequiredError, InvalidInputError, LLMConnectionError
from app.schemas.available_model import AvailableModelsQuery, LocalModelsQuery
from app.schemas.llm_config import LlmConfigCreate
from app.services.llm import chatgpt_auth, config_service, model_catalog, model_listing

Handler = Callable[[httpx.Request], httpx.Response]


def _use_transport(monkeypatch: pytest.MonkeyPatch, handler: Handler) -> list[httpx.Request]:
    """把 model_catalog 的 HTTP 呼叫導向假的 transport，記錄收到的請求。"""
    requests: list[httpx.Request] = []

    def recording_handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    real_client = httpx.AsyncClient

    def fake_client(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(recording_handler), **kwargs)

    monkeypatch.setattr(model_catalog.httpx, "AsyncClient", fake_client)
    return requests


async def _query(session: AsyncSession, **fields: Any) -> Any:
    return await model_listing.list_available_models(
        session, AvailableModelsQuery.model_validate(fields)
    )


async def test_ollama_lists_installed_models_from_default_base(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {"models": [{"name": "qwen3:8b"}, {"name": "llama3.2:latest"}]}
    requests = _use_transport(monkeypatch, lambda _: httpx.Response(200, json=payload))

    result = await _query(session, provider="ollama")

    assert [model.id for model in result.models] == ["llama3.2:latest", "qwen3:8b"]
    assert str(requests[0].url) == "http://localhost:11434/api/tags"


async def test_openai_keeps_only_chat_models_and_sends_bearer_key(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    ids = ["gpt-5.3-codex", "text-embedding-3-small", "whisper-1", "gpt-4o", "ft:gpt-4o:org::x"]
    payload = {"data": [{"id": model_id} for model_id in ids]}
    requests = _use_transport(monkeypatch, lambda _: httpx.Response(200, json=payload))

    result = await _query(session, provider="openai", api_key="sk-test-abcdefgh1234")

    assert [model.id for model in result.models] == ["ft:gpt-4o:org::x", "gpt-4o", "gpt-5.3-codex"]
    assert requests[0].headers["Authorization"] == "Bearer sk-test-abcdefgh1234"


async def test_gemini_lists_generate_content_models_with_display_name(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "models": [
            {
                "name": "models/gemini-3.5-flash",
                "displayName": "Gemini 3.5 Flash",
                "supportedGenerationMethods": ["generateContent", "countTokens"],
            },
            {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        ]
    }
    requests = _use_transport(monkeypatch, lambda _: httpx.Response(200, json=payload))

    result = await _query(session, provider="gemini", api_key="AIza-test-key-0000")

    assert [(model.id, model.label) for model in result.models] == [
        ("gemini-3.5-flash", "Gemini 3.5 Flash")
    ]
    assert requests[0].headers["x-goog-api-key"] == "AIza-test-key-0000"
    assert "key=" not in str(requests[0].url)


def _signed_in_chatgpt(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_credentials() -> chatgpt_auth.ChatgptCredentials:
        return chatgpt_auth.ChatgptCredentials(
            access_token="token-test", account_id="acct-test", api_base="https://codex.test"
        )

    monkeypatch.setattr(model_listing.chatgpt_auth, "ensure_access_token", fake_credentials)


async def test_chatgpt_lists_account_models_in_picker_order(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signed_in_chatgpt(monkeypatch)
    payload = {
        "models": [
            {"slug": "gpt-5.5", "display_name": "GPT-5.5", "visibility": "list", "priority": 9},
            {"slug": "gpt-6-sol", "display_name": "GPT-6 Sol", "visibility": "list", "priority": 2},
            {"slug": "internal-x", "display_name": "Internal", "visibility": "hide", "priority": 1},
        ]
    }
    requests = _use_transport(monkeypatch, lambda _: httpx.Response(200, json=payload))

    result = await _query(session, provider="chatgpt")

    assert [(model.id, model.label) for model in result.models] == [
        ("gpt-6-sol", "GPT-6 Sol"),
        ("gpt-5.5", "GPT-5.5"),
    ]
    request = requests[0]
    assert request.url.path == "/models"
    assert request.url.params["client_version"]
    assert request.headers["Authorization"] == "Bearer token-test"
    assert request.headers["ChatGPT-Account-Id"] == "acct-test"


async def test_chatgpt_expired_login_asks_to_sign_in_again(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _signed_in_chatgpt(monkeypatch)
    _use_transport(monkeypatch, lambda _: httpx.Response(401, json={"detail": "expired"}))

    with pytest.raises(ChatgptAuthRequiredError, match="重新登入"):
        await _query(session, provider="chatgpt")


async def test_chatgpt_without_login_is_rejected(session: AsyncSession) -> None:
    with pytest.raises(ChatgptAuthRequiredError, match="尚未登入"):
        await _query(session, provider="chatgpt")


async def test_invalid_key_returns_readable_error(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_transport(monkeypatch, lambda _: httpx.Response(401, json={"error": "bad"}))

    with pytest.raises(LLMConnectionError, match="API 金鑰無效"):
        await _query(session, provider="openai", api_key="sk-test-abcdefgh1234")


async def test_unreachable_server_names_the_host(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    _use_transport(monkeypatch, refuse)

    with pytest.raises(LLMConnectionError, match=r"無法連線到 127\.0\.0\.1:1234"):
        await _query(session, provider="openai_compatible", api_base="http://127.0.0.1:1234/v1")


async def test_missing_key_is_rejected_before_calling_service(session: AsyncSession) -> None:
    with pytest.raises(InvalidInputError, match="API 金鑰"):
        await _query(session, provider="gemini")


async def test_stored_key_is_used_only_for_the_same_provider(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await config_service.create_config(
        session,
        LlmConfigCreate(
            name="Codex",
            provider=LlmProvider.OPENAI,
            model="gpt-5.3-codex",
            api_key=SecretStr("sk-test-stored-key-9999"),
        ),
    )
    requests = _use_transport(monkeypatch, lambda _: httpx.Response(200, json={"data": []}))

    await _query(session, provider="openai", config_id=str(config.id))

    assert requests[0].headers["Authorization"] == "Bearer sk-test-stored-key-9999"
    with pytest.raises(InvalidInputError):
        await _query(session, provider="gemini", config_id=str(config.id))


async def _detect(session: AsyncSession, **fields: Any) -> Any:
    return await model_listing.detect_local_models(session, LocalModelsQuery.model_validate(fields))


async def test_local_detects_ollama_at_default_address(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_transport(
        monkeypatch, lambda _: httpx.Response(200, json={"models": [{"name": "qwen3:8b"}]})
    )

    result = await _detect(session)

    assert (result.provider, result.api_base) == (
        LlmProvider.OLLAMA,
        "http://localhost:11434",
    )
    assert [model.id for model in result.models] == ["qwen3:8b"]


async def test_local_detects_openai_compatible_and_appends_v1(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    def lm_studio(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/models":
            return httpx.Response(200, json={"data": [{"id": "qwen3-8b"}]})
        return httpx.Response(404, json={"error": "not found"})

    requests = _use_transport(monkeypatch, lm_studio)

    result = await _detect(session, api_base="http://127.0.0.1:1234")

    assert (result.provider, result.api_base) == (
        LlmProvider.OPENAI_COMPATIBLE,
        "http://127.0.0.1:1234/v1",
    )
    assert [request.url.path for request in requests] == ["/api/tags", "/v1/models"]


async def test_local_stops_trying_when_host_is_unreachable(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    requests = _use_transport(monkeypatch, refuse)

    with pytest.raises(LLMConnectionError, match="無法連線到 localhost:11434"):
        await _detect(session)
    assert len(requests) == 1


async def test_local_rejects_unrelated_server(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    _use_transport(monkeypatch, lambda _: httpx.Response(200, json={"hello": "world"}))

    with pytest.raises(LLMConnectionError, match="不是 Ollama 或 OpenAI 相容伺服器"):
        await _detect(session, api_base="http://127.0.0.1:8080")
