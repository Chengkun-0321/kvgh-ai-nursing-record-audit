"""ChatGPT 訂閱登入狀態。"""

from datetime import datetime

from pydantic import BaseModel

from app.core.enums import ChatgptAuthState


class ChatgptAuthStatusRead(BaseModel):
    """登入狀態；`pending` 時附上要在 OpenAI 頁面輸入的驗證碼。"""

    state: ChatgptAuthState
    account_email: str | None = None
    user_code: str | None = None
    verification_url: str | None = None
    expires_at: datetime | None = None
    # 上一次登入失敗的原因（例如驗證碼逾時）
    error_message: str | None = None
