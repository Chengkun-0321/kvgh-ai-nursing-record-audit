"""稽核日的「已結束」判斷與預設日期規則（純函式，不讀院方資料）。"""

from datetime import date

from app.services.audit.clock import default_business_date, is_day_ended


def test_day_is_ended_only_when_strictly_before_today() -> None:
    today = date(2026, 1, 2)

    assert is_day_ended(date(2026, 1, 1), today) is True
    assert is_day_ended(today, today) is False
    assert is_day_ended(date(2026, 1, 3), today) is False


def test_default_date_is_latest_ended_day() -> None:
    dates = [date(2026, 1, 1), date(2026, 1, 2)]

    assert default_business_date(dates, date(2026, 1, 2)) == date(2026, 1, 1)
    assert default_business_date(dates, date(2026, 1, 3)) == date(2026, 1, 2)


def test_default_date_falls_back_to_latest_when_no_day_has_ended() -> None:
    dates = [date(2026, 1, 1), date(2026, 1, 2)]

    assert default_business_date(dates, date(2026, 1, 1)) == date(2026, 1, 2)
