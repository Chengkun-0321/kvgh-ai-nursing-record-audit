"""Demo 登入的請求與回應。"""

from pydantic import BaseModel, Field

from app.core.constants import LOGIN_PASSWORD_MAX_LENGTH, LOGIN_USERNAME_MAX_LENGTH


class LoginRequest(BaseModel):
    """登入表單；長度上限避免送出過大的字串。"""

    username: str = Field(min_length=1, max_length=LOGIN_USERNAME_MAX_LENGTH)
    password: str = Field(min_length=1, max_length=LOGIN_PASSWORD_MAX_LENGTH)


class SessionRead(BaseModel):
    """目前登入的帳號。"""

    username: str
