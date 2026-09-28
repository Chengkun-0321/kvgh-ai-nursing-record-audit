from httpx import AsyncClient

from app.core.constants import LLM_SYSTEM_PROMPT_MAX_CHARS

_BASE = "/api/v1/llm-system-prompts"


async def test_saved_prompt_is_returned_as_current(client: AsyncClient) -> None:
    created = await client.post(
        _BASE, json={"content": "一律使用繁體中文回答。", "base_version": None}
    )

    current = await client.get(f"{_BASE}/current")

    assert created.status_code == 201, created.text
    assert current.json()["version"] == 1
    assert current.json()["content"] == "一律使用繁體中文回答。"


async def test_current_before_any_save_is_empty(client: AsyncClient) -> None:
    response = await client.get(f"{_BASE}/current")

    assert response.status_code == 200
    assert response.json() == {"version": None, "content": "", "created_at": None}


async def test_too_long_prompt_is_rejected(client: AsyncClient) -> None:
    too_long = "字" * (LLM_SYSTEM_PROMPT_MAX_CHARS + 1)
    response = await client.post(_BASE, json={"content": too_long, "base_version": None})

    assert response.status_code == 422


async def test_saving_from_outdated_page_returns_conflict(client: AsyncClient) -> None:
    await client.post(_BASE, json={"content": "v1 內容", "base_version": None})
    await client.post(_BASE, json={"content": "v2 內容", "base_version": 1})

    response = await client.post(_BASE, json={"content": "舊頁面", "base_version": 1})

    assert response.status_code == 409
    assert "v2" in response.json()["detail"]
