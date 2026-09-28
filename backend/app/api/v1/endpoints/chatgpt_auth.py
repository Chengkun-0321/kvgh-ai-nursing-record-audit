"""ChatGPT 訂閱登入 API。"""

from fastapi import APIRouter

from app.schemas.chatgpt_auth import ChatgptAuthStatusRead
from app.services.llm import chatgpt_auth

router = APIRouter(prefix="/chatgpt-auth", tags=["ChatGPT 訂閱登入"])


@router.get("", response_model=ChatgptAuthStatusRead, summary="取得 ChatGPT 登入狀態")
async def get_chatgpt_auth_status() -> ChatgptAuthStatusRead:
    return await chatgpt_auth.get_status()


@router.post(
    "/device-code", response_model=ChatgptAuthStatusRead, summary="開始 ChatGPT 裝置碼登入"
)
async def start_chatgpt_device_login() -> ChatgptAuthStatusRead:
    return await chatgpt_auth.start_device_login()


@router.delete("", response_model=ChatgptAuthStatusRead, summary="登出 ChatGPT")
async def sign_out_chatgpt() -> ChatgptAuthStatusRead:
    return await chatgpt_auth.sign_out()
