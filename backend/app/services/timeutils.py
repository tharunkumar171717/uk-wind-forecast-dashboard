"""Timezone helpers. All storage is UTC; business days are Europe/London local days."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

LONDON = ZoneInfo("Europe/London")


def local_day_bounds(d: date) -> tuple[datetime, datetime]:
    """UTC [start, end) of the Europe/London calendar day `d` (23/24/25 hours long)."""
    start = datetime.combine(d, time(0), tzinfo=LONDON).astimezone(UTC)
    end = datetime.combine(d + timedelta(days=1), time(0), tzinfo=LONDON).astimezone(UTC)
    return start, end


def range_bounds(start: date, end: date) -> tuple[datetime, datetime]:
    """UTC [start, end) covering local days start..end inclusive."""
    return local_day_bounds(start)[0], local_day_bounds(end)[1]


def hourly_index(start: date, end: date | None = None) -> pd.DatetimeIndex:
    """Hourly UTC delivery intervals for local days start..end inclusive."""
    lo, hi = range_bounds(start, end or start)
    return pd.date_range(lo, hi, freq="h", inclusive="left", tz="UTC")


def cutoff_for_day(d: date, cutoff_time: time, days_before: int) -> datetime:
    """Decision cutoff for delivery day `d`: local `cutoff_time` on D-`days_before`, as UTC."""
    local = datetime.combine(d - timedelta(days=days_before), cutoff_time, tzinfo=LONDON)
    return local.astimezone(UTC)


def london_date(ts: pd.Timestamp) -> date:
    return ts.tz_convert(LONDON).date()


def iter_days(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)
