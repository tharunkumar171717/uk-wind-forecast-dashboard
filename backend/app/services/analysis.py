"""Orchestrates source reads + pure selection/alignment, with an in-memory TTL cache."""

import threading
import time as _time
from datetime import date, time
from typing import Protocol

import pandas as pd

from app.services.alignment import align
from app.services.selection import select_for_days
from app.services.timeutils import cutoff_for_day, hourly_index, range_bounds


class Source(Protocol):
    mode: str

    def ping(self) -> None: ...
    def fetch_actuals(self, start, end) -> pd.DataFrame: ...
    def fetch_forecasts(self, start, end, max_publish) -> pd.DataFrame: ...
    def row_counts(self) -> dict: ...
    def last_ingestion(self) -> dict: ...


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self.ttl = ttl_seconds
        self._data: dict = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            hit = self._data.get(key)
            if hit and hit[0] > _time.monotonic():
                return hit[1]
            self._data.pop(key, None)
            return None

    def set(self, key, value) -> None:
        with self._lock:
            self._data[key] = (_time.monotonic() + self.ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class Analysis:
    """Aligned frame + whether any source data existed for the window."""

    def __init__(self, aligned: pd.DataFrame, has_data: bool):
        self.aligned = aligned
        self.has_data = has_data


def analyze(source: Source, start: date, end: date, cutoff_time: time, days_before: int) -> Analysis:
    lo, hi = range_bounds(start, end)
    max_cutoff = cutoff_for_day(end, cutoff_time, days_before)
    forecasts = source.fetch_forecasts(lo, hi, max_cutoff)
    actuals = source.fetch_actuals(lo, hi)
    selected = select_for_days(forecasts, start, end, cutoff_time, days_before)
    aligned = align(selected, actuals, hourly_index(start, end))
    return Analysis(aligned, has_data=not (forecasts.empty and actuals.empty))


def slice_window(result: Analysis, start: date, end: date) -> Analysis:
    """Rows of a wider analysis for local days start..end. Valid because selection is per delivery day."""
    lo, hi = range_bounds(start, end)
    df = result.aligned
    part = df[(df["start_time"] >= lo) & (df["start_time"] < hi)].reset_index(drop=True)
    has_data = bool(part["forecast_mw"].notna().any() or (part["quality"] != "missing_both").any())
    return Analysis(part, has_data)


def cached_analyze(
    cache: TTLCache,
    source: Source,
    start: date,
    end: date,
    cutoff_time: time,
    days_before: int,
    window: tuple[date, date] | None = None,
):
    """Analyse the whole evaluation `window` once (one DB round trip pair), then slice per request."""
    w_start, w_end = window or (start, end)
    key = (source.mode, w_start, w_end, cutoff_time, days_before)
    full = cache.get(key)
    if full is None:
        full = analyze(source, w_start, w_end, cutoff_time, days_before)
        cache.set(key, full)
    if (start, end) == (w_start, w_end):
        return full
    return slice_window(full, start, end)
