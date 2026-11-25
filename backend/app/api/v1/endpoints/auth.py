"""Demo 登入 API：登入、登出、查詢目前登入狀態。"""

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUsername
from app.schemas.auth import LoginRequest, SessionRead
from app.services import auth

router = APIRouter(prefix="/auth", tags=["登入"])


@router.post("/login", response_model=SessionRead, summary="以 demo 帳密登入")
async def login(payload: LoginRequest, response: Response) -> SessionRead:
    session = auth.login(payload.username, payload.password)
    response.set_cookie(
        auth.SESSION_COOKIE_NAME,
        session.token,
        max_age=session.max_age_seconds,
        # 不設 Secure：本機開發走 http，設了瀏覽器就不會送出 cookie
        path="/",
        httponly=True,
        samesite="lax",
    )
    return SessionRead(username=session.username)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="登出並清除 session cookie",
)
async def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(auth.SESSION_COOKIE_NAME, path="/", httponly=True, samesite="lax")
    return response


@router.get("/session", response_model=SessionRead, summary="取得目前登入的帳號")
async def get_session(username: CurrentUsername) -> SessionRead:
    return SessionRead(username=username)
