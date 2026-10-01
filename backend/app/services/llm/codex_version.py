"""決定查詢 ChatGPT 帳號模型清單時帶的 Codex 用戶端版本（`client_version`）。

Codex 後端依 `client_version` 篩選模型，版本太舊時新模型不會列出。
優先順序：設定檔固定的 `CHATGPT_CLIENT_VERSION` → npm 上 `@openai/codex` 的最新版本（記憶體快取）
→ `CHATGPT_CLIENT_VERSION_FALLBACK`。查詢只帶套件名稱，不含任何 token 或病患資料。
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Final

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS: Final = 5
# 查詢失敗時，短時間內不再重試，避免每次開啟模型清單都多等一次逾時
_FAILURE_CACHE_SECONDS: Final = 600
_VERSION_PATTERN: Final = re.compile(r"^\d+\.\d+\.\d+$")


class _NpmLatest(BaseModel):
    version: str


@dataclass(frozen=True)
class _CachedVersion:
    version: str
    expires_at: float


class _VersionCache:
    """模組層級的版本快取；以物件保存狀態，避免使用 global。"""

    def __init__(self) -> None:
        self.entry: _CachedVersion | None = None
        self.lock = asyncio.Lock()

    def get(self) -> str | None:
        if self.entry is None or time.monotonic() >= self.entry.expires_at:
            return None
        return self.entry.version

    def put(self, version: str, ttl_seconds: float) -> None:
        self.entry = _CachedVersion(version=version, expires_at=time.monotonic() + ttl_seconds)


_cache = _VersionCache()


async def resolve_client_version() -> str:
    """回傳查詢模型清單要帶的 Codex 用戶端版本；自動查詢失敗時退回預設值，不拋例外。"""
    settings = get_settings()
    if settings.CHATGPT_CLIENT_VERSION:
        return settings.CHATGPT_CLIENT_VERSION

    async with _cache.lock:
        cached = _cache.get()
        if cached is not None:
            return cached
        latest = await _fetch_latest_version(settings.CODEX_LATEST_VERSION_URL)
        if latest is None:
            _cache.put(settings.CHATGPT_CLIENT_VERSION_FALLBACK, _FAILURE_CACHE_SECONDS)
            return settings.CHATGPT_CLIENT_VERSION_FALLBACK
        _cache.put(latest, settings.CODEX_VERSION_CACHE_SECONDS)
        return latest


def reset_cache() -> None:
    """清除快取的版本（供測試使用）。"""
    _cache.entry = None


async def _fetch_latest_version(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        response.raise_for_status()
        version = _NpmLatest.model_validate(response.json()).version
    except (httpx.HTTPError, ValueError, ValidationError) as exc:
        logger.warning("無法取得 Codex 最新版本，改用預設版本：%s", type(exc).__name__)
        return None
    if not _VERSION_PATTERN.match(version):
        logger.warning("Codex 最新版本格式無法辨識，改用預設版本：%s", version)
        return None
    logger.info("已取得 Codex 最新版本：%s", version)
    return version
