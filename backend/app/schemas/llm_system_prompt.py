"""共用 system prompt 的輸入與輸出結構。"""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.core.constants import LLM_SYSTEM_PROMPT_MAX_CHARS


class LlmSystemPromptCreate(BaseModel):
    """儲存新版本；空字串表示不使用 system prompt。"""

    content: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=LLM_SYSTEM_PROMPT_MAX_CHARS)
    ]
    # 開始編輯時的版本（從未儲存過為 null）；已不是最新版本時拒絕，避免舊頁面覆寫較新的內容
    base_version: int | None


class LlmSystemPromptRead(BaseModel):
    """目前使用的版本；尚未儲存過時 `version`、`created_at` 為 null。"""

    version: int | None
    content: str
    created_at: datetime | None
