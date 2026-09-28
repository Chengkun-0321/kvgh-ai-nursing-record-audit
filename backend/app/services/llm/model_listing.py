"""查詢各服務可用的模型，供設定頁的模型下拉選單使用。

HTTP 查詢在 `model_catalog`，LiteLLM 價格表查詢在 `gateway`，ChatGPT 登入 token 在 `chatgpt_auth`；
本模組負責取得查詢用的金鑰（輸入值，或解密已儲存的金鑰，只在查詢當下使用）。
"""

import logging
import uuid
from typing import Final

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import LlmProvider
from app.core.exceptions import ChatgptAuthRequiredError
from app.core.security import decrypt_secret
from app.schemas.available_model import (
    AvailableModel,
    AvailableModelsQuery,
    AvailableModelsRead,
    LocalModelsQuery,
    LocalModelsRead,
)
from app.services.llm import chatgpt_auth, config_service, gateway, model_catalog
from app.services.llm.providers import (
    OLLAMA_DEFAULT_API_BASE,
    check_required_fields,
    resolve_api_base,
)

logger = logging.getLogger(__name__)

# 「本地模型」涵蓋的兩種伺服器；已儲存的金鑰在兩者間可沿用
_LOCAL_PROVIDERS: Final = frozenset({LlmProvider.OLLAMA, LlmProvider.OPENAI_COMPATIBLE})


async def list_available_models(
    session: AsyncSession, query: AvailableModelsQuery
) -> AvailableModelsRead:
    """查詢該服務目前可用的模型，供設定頁的下拉選單使用。

    ChatGPT 訂閱以登入 token 查詢「此帳號」可用的模型（與 Codex 的模型選單相同）。

    Raises:
        InvalidInputError: 缺少該服務類型查詢所需的 API 金鑰或 API 位址。
        ChatgptAuthRequiredError: ChatGPT 訂閱尚未登入或登入已失效。
        NotFoundError: `config_id` 指定的設定不存在。
        LLMConnectionError: 無法取得清單（連線失敗、金鑰無效…）。
    """
    if query.provider == LlmProvider.CHATGPT:
        return AvailableModelsRead(models=await _list_chatgpt_models())

    api_key = await _resolve_listing_key(
        session, query.api_key, query.config_id, frozenset({query.provider})
    )
    api_base = resolve_api_base(query.provider, query.api_base)
    check_required_fields(query.provider, has_api_key=api_key is not None, api_base=api_base)
    target = model_catalog.ListingTarget(query.provider, api_base=api_base, api_key=api_key)
    models = await model_catalog.fetch_models(target)
    if query.provider in model_catalog.CHAT_FILTERED_PROVIDERS:
        models = [
            model
            for model in models
            if model_catalog.is_chat_model(
                model.id, gateway.lookup_model_mode(query.provider, model.id)
            )
        ]
    logger.info("已查詢可用模型：provider=%s count=%d", query.provider, len(models))
    return AvailableModelsRead(models=sorted(models, key=lambda model: model.id))


async def detect_local_models(session: AsyncSession, query: LocalModelsQuery) -> LocalModelsRead:
    """偵測本地伺服器類型（Ollama／OpenAI 相容）並列出可用模型。

    Raises:
        NotFoundError: `config_id` 指定的設定不存在。
        LLMConnectionError: 無法連線、金鑰無效，或此位址不是支援的伺服器。
    """
    api_key = await _resolve_listing_key(session, query.api_key, query.config_id, _LOCAL_PROVIDERS)
    listing = await model_catalog.detect_local_models(
        query.api_base or OLLAMA_DEFAULT_API_BASE, api_key
    )
    logger.info("已偵測本地伺服器：provider=%s count=%d", listing.provider, len(listing.models))
    return LocalModelsRead(
        provider=listing.provider,
        api_base=listing.api_base,
        models=sorted(listing.models, key=lambda model: model.id),
    )


async def _resolve_listing_key(
    session: AsyncSession,
    api_key: SecretStr | None,
    config_id: uuid.UUID | None,
    accepted_providers: frozenset[LlmProvider],
) -> str | None:
    if api_key is not None:
        return api_key.get_secret_value().strip() or None
    if config_id is None:
        return None
    stored = await config_service.get_stored_config(session, config_id)
    # 換了服務類型時，已儲存的金鑰屬於另一個服務，不可拿去查詢
    if stored.provider not in accepted_providers or stored.api_key_encrypted is None:
        return None
    return decrypt_secret(stored.api_key_encrypted)


async def _list_chatgpt_models() -> list[AvailableModel]:
    credentials = await chatgpt_auth.ensure_access_token()
    target = model_catalog.ListingTarget(
        LlmProvider.CHATGPT,
        api_base=credentials.api_base,
        api_key=None,
        headers=chatgpt_auth.request_headers(credentials),
        params={"client_version": get_settings().CHATGPT_CLIENT_VERSION},
    )
    try:
        models = await model_catalog.fetch_models(target)
    except model_catalog.ListingUnauthorizedError as exc:
        raise ChatgptAuthRequiredError("ChatGPT 登入已失效，請重新登入") from exc
    logger.info("已查詢 ChatGPT 帳號可用模型：count=%d", len(models))
    # 保留 Codex 模型選單的順序，不重新排序
    return models
