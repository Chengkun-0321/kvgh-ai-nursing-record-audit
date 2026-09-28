"""建立 FastAPI app：middleware、exception handler、router。"""

import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any, Final

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.session import dispose_engine
from app.services.llm import chatgpt_auth

logger = logging.getLogger(__name__)

_API_PREFIX: Final = "/api/v1"
_ALLOWED_METHODS: Final = ["GET", "POST", "PATCH", "DELETE"]


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    chatgpt_auth.configure_token_dir(settings.CHATGPT_TOKEN_DIR)
    yield
    await dispose_engine()


async def _handle_app_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # 只註冊給 AppError，型別由 Starlette 介面決定
        raise exc
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise exc
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": _describe_validation_errors(exc.errors())},
    )


def _describe_validation_errors(errors: Sequence[Any]) -> str:
    # schema 內自訂的 ValueError 訊息已是繁中，優先顯示；其餘只列出欄位名稱
    custom_messages = [
        str(error["ctx"]["error"])
        for error in errors
        if error.get("type") == "value_error" and "error" in error.get("ctx", {})
    ]
    if custom_messages:
        return "；".join(dict.fromkeys(custom_messages))
    fields = sorted({str(error["loc"][-1]) for error in errors if error.get("loc")})
    detail = "輸入資料格式不正確"
    return f"{detail}，請檢查欄位：{'、'.join(fields)}" if fields else detail


async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    # 前端不顯示 stack trace；log 只記例外類型，避免帶出請求內容
    logger.error("未預期的錯誤：%s", type(exc).__name__)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "伺服器發生錯誤，請稍後再試"},
    )


def create_app() -> FastAPI:
    """建立 FastAPI app。"""
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="高榮 AI 護理紀錄稽核 API", lifespan=_lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_methods=_ALLOWED_METHODS,
        allow_headers=["Content-Type"],
    )
    app.add_exception_handler(AppError, _handle_app_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
    app.include_router(api_router, prefix=_API_PREFIX)
    return app


app = create_app()
