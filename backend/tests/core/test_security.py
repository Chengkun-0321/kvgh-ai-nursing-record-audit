import pytest
from cryptography.fernet import Fernet

from app.core import security
from app.core.exceptions import SecretDecryptError


def test_encrypt_then_decrypt_returns_original() -> None:
    token = security.encrypt_secret("sk-test-1234567890")

    assert token != "sk-test-1234567890"
    assert security.decrypt_secret(token) == "sk-test-1234567890"


def test_decrypt_with_foreign_token_raises_readable_error() -> None:
    foreign_token = Fernet(Fernet.generate_key()).encrypt(b"sk-test").decode()

    with pytest.raises(SecretDecryptError, match="重新輸入 API 金鑰"):
        security.decrypt_secret(foreign_token)


def test_mask_secret_keeps_prefix_and_last_four() -> None:
    assert security.mask_secret("sk-proj-abcdefgh1234") == "sk-…1234"


def test_mask_secret_hides_short_values_entirely() -> None:
    assert security.mask_secret("short") == "••••"
