"""稽核用的「今天」與「已結束的日子」判斷。

「已結束」定義：稽核日 < 今天（Asia/Taipei）。今天未結束時，之後才寫的紀錄不會被稽核到。
`TodayProvider` 讓測試注入固定日期；正式環境用 `taipei_today`。
"""

from collections.abc import Callable, Sequence
from datetime import date, datetime

from app.services.hospital_data.times import TAIPEI

TodayProvider = Callable[[], date]


def taipei_today() -> date:
    """台北時間的今天。"""
    return datetime.now(TAIPEI).date()


def is_day_ended(business_date: date, today: date) -> bool:
    """稽核日是否已結束（早於今天）。"""
    return business_date < today


def default_business_date(dates: Sequence[date], today: date) -> date:
    """未指定稽核日時的預設日：已結束的最新一天；沒有任何已結束的日子時為最新一天。

    `dates` 必須非空（呼叫端已確認該病人或病房有資料）。
    """
    ended = [day for day in dates if is_day_ended(day, today)]
    return max(ended) if ended else max(dates)
