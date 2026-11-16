"""稽核用的文字正規化：院方原文含格式字元與變體選擇器（如 U+E01B5），比對前先去除。"""

import unicodedata
from typing import Final

_NOISE_CATEGORIES: Final = frozenset({"Cf", "Co", "Cn"})
_VARIATION_SELECTOR_RANGES: Final = ((0xFE00, 0xFE0F), (0xE0100, 0xE01EF))


def remove_noise(raw: str) -> str:
    """去除格式字元、私用區字元與變體選擇器；其餘字元（含空白）原樣保留。"""
    return "".join(char for char in raw if not _is_noise(char))


def normalize_text(raw: str) -> str:
    """統一換行、去除雜訊字元並摺疊空白，供相似度比對使用。"""
    unified = raw.replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(remove_noise(unified).split())


def squash(raw: str) -> str:
    """去除雜訊字元與所有空白，供 Evidence 原文核對使用（排版差異不影響比對）。"""
    return "".join(remove_noise(raw).split())


def _is_noise(char: str) -> bool:
    if unicodedata.category(char) in _NOISE_CATEGORIES:
        return True
    code = ord(char)
    return any(low <= code <= high for low, high in _VARIATION_SELECTOR_RANGES)
