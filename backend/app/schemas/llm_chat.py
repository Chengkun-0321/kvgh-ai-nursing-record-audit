"""測試對話的請求與串流事件。"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.core.constants import CHAT_MAX_MESSAGE_CHARS, CHAT_MAX_MESSAGES
from app.core.enums import ChatRole


class ChatMessage(BaseModel):
    """一則對話訊息。"""

    role: ChatRole
    content: Annotated[str, StringConstraints(min_length=1, max_length=CHAT_MAX_MESSAGE_CHARS)]


class ChatRequest(BaseModel):
    """測試對話請求：對話歷史只存在前端，每次送出完整訊息。"""

    messages: Annotated[list[ChatMessage], Field(min_length=1, max_length=CHAT_MAX_MESSAGES)]

    @field_validator("messages")
    @classmethod
    def _last_message_is_from_user(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        if messages[-1].role != ChatRole.USER:
            raise ValueError("最後一則訊息必須是使用者訊息")
        return messages


class ChatDeltaEvent(BaseModel):
    """模型回應的一段文字。"""

    type: Literal["delta"]
    text: str


class ChatDoneEvent(BaseModel):
    """回應完成：附模型名稱、耗時、token 用量（服務未提供時為 null）與所用的 system prompt 版本。"""

    type: Literal["done"]
    model: str
    latency_ms: int
    # 送出到收到第一段文字的時間；沒有任何文字時為 null
    first_token_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    # 未設定共用 system prompt（或內容為空）時為 null
    system_prompt_version: int | None


class ChatErrorEvent(BaseModel):
    """串流途中發生錯誤。"""

    type: Literal["error"]
    message: str


ChatStreamEvent = Annotated[
    ChatDeltaEvent | ChatDoneEvent | ChatErrorEvent, Field(discriminator="type")
]
