import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import AsyncClient
from litellm import exceptions as litellm_errors

from app.services.llm import gateway

_BASE = "/api/v1/llm-configs"


async def _create(client: AsyncClient, **fields: object) -> dict[str, Any]:
    payload = {"name": "本地 Ollama", "provider": "ollama", "model": "llama3.2", **fields}
    response = await client.post(_BASE, json=payload)
    assert response.status_code == 201, response.text
    return dict(response.json())


def _sse_events(body: str) -> list[dict[str, Any]]:
    return [
        json.loads(line.removeprefix("data: "))
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


async def test_saved_configs_survive_new_requests(client: AsyncClient) -> None:
    first = await _create(client)
    await _create(
        client, name="Codex", provider="openai", model="gpt-5.3-codex", api_key="sk-x" * 5
    )

    response = await client.get(_BASE)

    configs = response.json()
    assert [config["name"] for config in configs] == ["本地 Ollama", "Codex"]
    assert configs[0]["id"] == first["id"]
    assert configs[0]["is_active"] is True
    assert configs[1]["has_api_key"] is True
    assert "api_key" not in configs[1]


async def test_blank_api_base_is_treated_as_unset(client: AsyncClient) -> None:
    created = await _create(client, api_base="  ")

    assert created["api_base"] is None


async def test_invalid_api_base_returns_chinese_message(client: AsyncClient) -> None:
    response = await client.post(
        _BASE, json={"name": "x", "provider": "ollama", "model": "m", "api_base": "localhost:11434"}
    )

    assert response.status_code == 422
    assert "http://" in response.json()["detail"]


async def test_activate_and_delete_flow(client: AsyncClient) -> None:
    first = await _create(client)
    second = await _create(client, name="第二組")

    activated = await client.post(f"{_BASE}/{second['id']}/activate")
    blocked = await client.delete(f"{_BASE}/{second['id']}")
    deleted = await client.delete(f"{_BASE}/{first['id']}")

    assert activated.json()["is_active"] is True
    assert blocked.status_code == 409
    assert deleted.status_code == 204


async def test_chat_streams_sse_events(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create(client)

    async def fake_stream() -> AsyncIterator[Any]:
        for text in ("測", "試"):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])

    async def fake_acompletion(**_: Any) -> AsyncIterator[Any]:
        return fake_stream()

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    response = await client.post(
        f"{_BASE}/{config['id']}/chat", json={"messages": [{"role": "user", "content": "你好"}]}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _sse_events(response.text)
    assert [event["type"] for event in events] == ["delta", "delta", "done"]
    assert "".join(event.get("text", "") for event in events) == "測試"


async def test_chat_open_failure_returns_http_error(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = await _create(client)

    async def fake_acompletion(**_: Any) -> None:
        raise litellm_errors.NotFoundError(message="nope", model="x", llm_provider="ollama")

    monkeypatch.setattr(gateway.litellm, "acompletion", fake_acompletion)

    response = await client.post(
        f"{_BASE}/{config['id']}/chat", json={"messages": [{"role": "user", "content": "你好"}]}
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "找不到模型「llama3.2」，請確認模型名稱"


async def test_chat_rejects_history_ending_with_assistant(client: AsyncClient) -> None:
    config = await _create(client)

    response = await client.post(
        f"{_BASE}/{config['id']}/chat",
        json={"messages": [{"role": "assistant", "content": "嗨"}]},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "最後一則訊息必須是使用者訊息"


async def test_available_models_for_chatgpt_requires_login(client: AsyncClient) -> None:
    response = await client.post("/api/v1/available-models", json={"provider": "chatgpt"})

    assert response.status_code == 409
    assert "尚未登入" in response.json()["detail"]
