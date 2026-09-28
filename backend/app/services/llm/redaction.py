"""把服務回傳的錯誤說明轉成可顯示的短句：遮蔽金鑰、去掉 LiteLLM 前綴、限制長度。"""

import re
from typing import Final

_DETAIL_MAX_CHARS: Final = 160
_MASK: Final = "••••"
# 服務錯誤訊息偶爾會帶出部分金鑰（OpenAI sk-…、Google AIza…）
_SECRET_PATTERN: Final = re.compile(r"(sk-|AIza)[A-Za-z0-9_\-]{6,}")


def redact_provider_detail(message: str, secret: str | None) -> str:
    """遮蔽訊息中的金鑰並截短。

    Args:
        message: 服務或 LiteLLM 的原始錯誤說明。
        secret: 本次呼叫使用的金鑰明文；有值時先整段遮蔽。

    Returns:
        可附在繁中錯誤訊息後的短說明。
    """
    if secret:
        message = message.replace(secret, _MASK)
    message = _SECRET_PATTERN.sub(_MASK, message)
    # LiteLLM 會在前面加上 `litellm.BadRequestError: OpenAIException - ` 之類的前綴
    return message.rsplit(" - ", 1)[-1].strip()[:_DETAIL_MAX_CHARS]
