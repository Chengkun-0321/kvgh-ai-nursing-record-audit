"""設定精靈表單檢查與服務類型目錄 API（規則原本在前端，改由後端提供）。"""

from typing import Any

import pytest
from httpx import AsyncClient

from app.core.enums import ChatgptAuthState
from app.schemas.chatgpt_auth import ChatgptAuthStatusRead
from app.services.llm import chatgpt_auth

_CHECK = "/api/v1/llm-configs/draft-checks"


async def _check(client: AsyncClient, **fields: object) -> dict[str, Any]:
    payload = {"name": "測試", "model": "m", **fields}
    response = await client.post(_CHECK, json=payload)
    assert response.status_code == 200, response.text
    return dict(response.json())


def _errors(body: dict[str, Any]) -> dict[str, str]:
    return {error["field"]: error["message"] for error in body["errors"]}


async def _create_config(client: AsyncClient, **fields: object) -> str:
    response = await client.post(
        "/api/v1/llm-configs", json={"name": "已存", "model": "m", **fields}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


@pytest.fixture
def chatgpt_signed_in(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _signed_in() -> ChatgptAuthStatusRead:
        return ChatgptAuthStatusRead(state=ChatgptAuthState.SIGNED_IN, account_email=None)

    monkeypatch.setattr(chatgpt_auth, "get_status", _signed_in)


async def test_required_api_key_is_reported(client: AsyncClient) -> None:
    body = await _check(client, provider="openai")
    assert body["is_valid"] is False
    assert _errors(body) == {"api_key": "請輸入 API 金鑰"}


async def test_stored_key_allows_blank_key(client: AsyncClient) -> None:
    config_id = await _create_config(client, provider="openai", api_key="sk-" + "x" * 20)
    body = await _check(client, provider="openai", config_id=config_id)
    assert body["is_valid"] is True
    assert body["keeps_stored_api_key"] is True


async def test_switching_provider_drops_stored_key(client: AsyncClient) -> None:
    config_id = await _create_config(client, provider="openai", api_key="sk-" + "x" * 20)
    body = await _check(client, provider="gemini", config_id=config_id)
    assert body["keeps_stored_api_key"] is False
    assert "api_key" in _errors(body)


async def test_openai_compatible_requires_valid_api_base(client: AsyncClient) -> None:
    missing = await _check(client, provider="openai_compatible")
    invalid = await _check(client, provider="openai_compatible", api_base="localhost:1234")
    assert _errors(missing)["api_base"] == "請輸入 API 位址"
    assert "http://" in _errors(invalid)["api_base"]


async def test_timeout_out_of_range(client: AsyncClient) -> None:
    body = await _check(client, provider="ollama", timeout_seconds="1")
    assert _errors(body) == {"timeout_seconds": "請輸入 5–600 的整數"}


async def test_lengths_match_save_limits(client: AsyncClient) -> None:
    body = await _check(
        client,
        provider="openai_compatible",
        model="m" * 201,
        api_base="http://h/" + "a" * 500,
        api_key="k" * 1001,
    )
    assert set(_errors(body)) == {"api_base", "api_key", "model"}


@pytest.mark.parametrize("timeout_text", ["²", "１２０", "1.5"])
async def test_timeout_accepts_ascii_digits_only(client: AsyncClient, timeout_text: str) -> None:
    body = await _check(client, provider="ollama", timeout_seconds=timeout_text)
    assert "timeout_seconds" in _errors(body)


async def test_clearing_stored_key_keeps_hint(client: AsyncClient) -> None:
    config_id = await _create_config(client, provider="openai", api_key="sk-" + "x" * 20)
    body = await _check(client, provider="openai", config_id=config_id, clear_api_key=True)
    assert body["keeps_stored_api_key"] is False
    assert body["stored_api_key_hint"] is not None


async def test_errors_follow_wizard_order(client: AsyncClient) -> None:
    body = await _check(client, provider="ollama", name="", model="")
    assert [error["field"] for error in body["errors"]] == ["model", "name"]


async def test_step_only_checks_its_fields(client: AsyncClient) -> None:
    body = await _check(client, provider="openai", model="", step_id="connection")
    assert [error["field"] for error in body["errors"]] == ["api_key"]


async def test_suggested_name_uses_provider_label(client: AsyncClient) -> None:
    body = await _check(client, provider="ollama", model="qwen3:8b")
    assert body["suggested_name"] == "本地模型（Ollama）・qwen3:8b"


async def test_remote_without_key_is_blocked(client: AsyncClient) -> None:
    body = await _check(client, provider="openai")
    assert body["model_list"] == {
        "kind": "blocked",
        "reason": "請先回上一步填寫 API 金鑰。",
        "config_id": None,
    }


async def test_chatgpt_requires_sign_in(client: AsyncClient) -> None:
    body = await _check(client, provider="chatgpt")
    assert body["model_list"]["kind"] == "blocked"


@pytest.mark.usefixtures("chatgpt_signed_in")
async def test_chatgpt_signed_in_queries_remote(client: AsyncClient) -> None:
    body = await _check(client, provider="chatgpt")
    assert body["model_list"]["kind"] == "remote"


async def test_local_blank_api_base_uses_default(client: AsyncClient) -> None:
    body = await _check(client, provider="ollama")
    assert body["model_list"] == {"kind": "local", "reason": None, "config_id": None}


async def test_local_stored_key_shared_between_local_providers(client: AsyncClient) -> None:
    config_id = await _create_config(
        client, provider="openai_compatible", api_base="http://localhost:1234/v1", api_key="k" * 8
    )
    body = await _check(client, provider="ollama", config_id=config_id)
    assert body["model_list"]["config_id"] == config_id


async def test_local_invalid_api_base_is_blocked(client: AsyncClient) -> None:
    body = await _check(client, provider="ollama", api_base="localhost")
    assert body["model_list"]["kind"] == "blocked"


async def test_draft_summary(client: AsyncClient) -> None:
    body = await _check(client, provider="ollama", model="llama3.2")
    assert body["summary_rows"] == [
        {"label": "服務類型", "value": "本地模型（Ollama）"},
        {"label": "伺服器位址", "value": "http://localhost:11434（預設）"},
        {"label": "API 金鑰", "value": "不需要"},
        {"label": "模型", "value": "llama3.2"},
        {"label": "逾時", "value": "預設 60 秒"},
    ]


async def test_saved_config_includes_label_and_summary(client: AsyncClient) -> None:
    await _create_config(client, provider="ollama", timeout_seconds=30)
    config = (await client.get("/api/v1/llm-configs")).json()[0]
    assert config["provider_label"] == "本地模型（Ollama）"
    assert {"label": "逾時", "value": "30 秒"} in config["summary_rows"]


async def test_provider_catalog(client: AsyncClient) -> None:
    response = await client.get("/api/v1/llm-providers")
    body = response.json()
    assert [choice["choice"] for choice in body["choices"]] == [
        "openai",
        "chatgpt",
        "gemini",
        "local",
    ]
    assert body["limits"]["timeout_max_seconds"] == 600
    providers = {option["provider"]: option for option in body["providers"]}
    assert providers["openai_compatible"]["api_base"] == "required"
    assert providers["ollama"]["choice"] == "local"
