"""機密加解密：LLM API key 以 Fernet 加密存 DB。"""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings
from app.core.exceptions import SecretDecryptError

# 太短的值只顯示遮罩，避免露出大部分內容
_MASK_MIN_LENGTH = 12
_MASK_PREFIX_LENGTH = 3
_MASK_SUFFIX_LENGTH = 4
_MASK_PLACEHOLDER = "••••"


def _fernet() -> Fernet:
    key = get_settings().LLM_KEY_ENCRYPTION_KEY.get_secret_value()
    return Fernet(key.encode())


def encrypt_secret(plain: str) -> str:
    """加密機密字串。

    Args:
        plain: 明文，例如 API key。

    Returns:
        可存入 DB 的 Fernet token。
    """
    return _fernet().encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    """解密機密字串；只在呼叫模型當下使用，結果不可快取或寫入 log。

    Args:
        token: `encrypt_secret` 產生的 Fernet token。

    Returns:
        明文。

    Raises:
        SecretDecryptError: 加密金鑰已變更或資料損毀。
    """
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise SecretDecryptError(
            "已儲存的 API 金鑰無法解密，加密金鑰可能已變更，請重新輸入 API 金鑰"
        ) from exc


def mask_secret(plain: str) -> str:
    """產生可顯示於畫面的遮罩值，例如 `sk-…abcd`。

    Args:
        plain: 明文。

    Returns:
        遮罩後的字串；過短時只回傳遮罩符號。
    """
    if len(plain) < _MASK_MIN_LENGTH:
        return _MASK_PLACEHOLDER
    return f"{plain[:_MASK_PREFIX_LENGTH]}…{plain[-_MASK_SUFFIX_LENGTH:]}"
