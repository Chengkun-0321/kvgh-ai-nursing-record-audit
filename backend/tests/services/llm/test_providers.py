import pytest

from app.core.enums import LlmProvider
from app.core.exceptions import InvalidInputError
from app.services.llm import providers


def test_every_provider_has_spec() -> None:
    assert set(providers.PROVIDER_SPECS) == set(LlmProvider)


@pytest.mark.parametrize(
    ("provider", "expected"),
    [
        (LlmProvider.OPENAI, "openai/gpt-5.3-codex"),
        # Codex 後端只接受 Responses API，一律加上 responses/
        (LlmProvider.CHATGPT, "chatgpt/responses/gpt-5.3-codex"),
        (LlmProvider.GEMINI, "gemini/gpt-5.3-codex"),
        (LlmProvider.OLLAMA, "ollama_chat/gpt-5.3-codex"),
        (LlmProvider.OPENAI_COMPATIBLE, "openai/gpt-5.3-codex"),
    ],
)
def test_build_litellm_model_adds_provider_prefix(provider: LlmProvider, expected: str) -> None:
    assert providers.build_litellm_model(provider, "gpt-5.3-codex") == expected


def test_ollama_without_api_base_uses_default() -> None:
    assert providers.resolve_api_base(LlmProvider.OLLAMA, None) == "http://localhost:11434"


def test_openai_without_api_key_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match="API 金鑰"):
        providers.check_required_fields(LlmProvider.OPENAI, has_api_key=False, api_base=None)


def test_openai_compatible_without_api_base_is_rejected() -> None:
    with pytest.raises(InvalidInputError, match="API 位址"):
        providers.check_required_fields(
            LlmProvider.OPENAI_COMPATIBLE, has_api_key=False, api_base=None
        )


def test_chatgpt_needs_neither_key_nor_api_base() -> None:
    providers.check_required_fields(LlmProvider.CHATGPT, has_api_key=False, api_base=None)
