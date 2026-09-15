from __future__ import annotations

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PRE_START = time(4, 0)
REGULAR_START = time(9, 30)
REGULAR_END = time(16, 0)
AFTER_END = time(20, 0)
EARLY_CLOSE_END = time(13, 0)

# NYSE full-day holidays we care about for the next couple of years.
NYSE_HOLIDAYS = {
    date(2025, 1, 1),
    date(2025, 1, 20),
    date(2025, 2, 17),
    date(2025, 4, 18),
    date(2025, 5, 26),
    date(2025, 6, 19),
    date(2025, 7, 4),
    date(2025, 9, 1),
    date(2025, 11, 27),
    date(2025, 12, 25),
    date(2026, 1, 1),
    date(2026, 1, 19),
    date(2026, 2, 16),
    date(2026, 4, 3),
    date(2026, 5, 25),
    date(2026, 6, 19),
    date(2026, 7, 3),
    date(2026, 9, 7),
    date(2026, 11, 26),
    date(2026, 12, 25),
}

NYSE_EARLY_CLOSE = {
    date(2025, 7, 3),
    date(2025, 11, 28),
    date(2025, 12, 24),
    date(2026, 11, 27),
    date(2026, 12, 24),
}

WEEKDAY_ZH = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def us_equity_session(now: datetime | None = None) -> dict[str, object]:
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    et_now = moment.astimezone(ET)
    today = et_now.date()
    clock = et_now.time()
    weekday = et_now.weekday()
    holiday = today in NYSE_HOLIDAYS
    early = today in NYSE_EARLY_CLOSE
    regular_end = EARLY_CLOSE_END if early else REGULAR_END

    if weekday >= 5:
        session = "closed"
        label = "周末休市"
    elif holiday:
        session = "closed"
        label = "休市"
    elif clock < PRE_START:
        session = "closed"
        label = "未开盘"
    elif clock < REGULAR_START:
        session = "pre"
        label = "盘前"
    elif clock < regular_end:
        session = "regular"
        label = "盘中"
    elif clock < AFTER_END:
        session = "after"
        label = "盘后"
    else:
        session = "closed"
        label = "已收盘"

    return {
        "session": session,
        "label": label,
        "et_time": et_now.strftime("%H:%M ET"),
        "et_date": today.isoformat(),
        "weekday": WEEKDAY_ZH[weekday],
        "holiday": holiday,
        "early_close": early,
    }
