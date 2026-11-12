"""院方時間字串的解析：沒有時區，一律視為台北時間。"""

from dataclasses import dataclass
from datetime import datetime
from typing import Final
from zoneinfo import ZoneInfo

from app.core.constants import BUSINESS_TIMEZONE

TAIPEI: Final = ZoneInfo(BUSINESS_TIMEZONE)
# 「YYYY-MM-DD」的長度；只有日期時畫面不顯示時刻
_DATE_ONLY_LENGTH: Final = 10


@dataclass(frozen=True)
class RecordTime:
    """解析後的紀錄時間；無法解析時 `occurred_at` 為 `None`，原文仍保留在 `text`。"""

    text: str
    occurred_at: datetime | None
    is_date_only: bool


def parse_record_time(text: str) -> RecordTime:
    """解析「YYYY-MM-DD」「YYYY-MM-DD HH:MM」「YYYY-MM-DD HH:MM:SS」。"""
    stripped = text.strip()
    try:
        parsed = datetime.fromisoformat(stripped)
    except ValueError:
        return RecordTime(text=text, occurred_at=None, is_date_only=False)
    return RecordTime(
        text=text,
        occurred_at=parsed.replace(tzinfo=TAIPEI),
        is_date_only=len(stripped) == _DATE_ONLY_LENGTH,
    )
