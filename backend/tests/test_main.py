import logging
import traceback

import pytest
from starlette.requests import Request

from app.main import _handle_unexpected_error

# 例外訊息模擬帶有病患資料與金鑰，log 不可出現
_SENSITIVE_MESSAGE = "病患 王小明 A123456789 sk-test-secret"


def _fail_with_sensitive_message() -> None:
    raise ValueError(_SENSITIVE_MESSAGE)


def _fail_from_cause() -> None:
    try:
        _fail_with_sensitive_message()
    except ValueError as exc:
        raise RuntimeError(_SENSITIVE_MESSAGE) from exc


def _raised_error() -> RuntimeError:
    try:
        _fail_from_cause()
    except RuntimeError as exc:
        return exc
    raise AssertionError


async def test_unexpected_error_log_has_locations_but_no_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    error = _raised_error()
    assert error.__cause__ is not None
    cause_frame = traceback.extract_tb(error.__cause__.__traceback__)[-1]

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = await _handle_unexpected_error(Request({"type": "http"}), error)

    assert response.status_code == 500
    [record] = caplog.records
    logged = record.getMessage()
    assert "RuntimeError" in logged
    assert "ValueError" in logged
    assert f"test_main.py:{cause_frame.lineno} _fail_with_sensitive_message" in logged
    assert "_fail_from_cause" in logged
    assert "王小明" not in logged
    assert "sk-test" not in logged
    # 原始碼行文字（raise ValueError(...)）也不可出現
    assert "raise ValueError" not in logged
    assert record.exc_info is None
