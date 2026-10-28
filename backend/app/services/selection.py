"""Decision-time forecast selection (no leakage): latest vintage published at or before the cutoff."""

from datetime import date, time

import pandas as pd

from app.services.timeutils import cutoff_for_day, hourly_index, iter_days

SELECTED_COLUMNS = ["start_time", "forecast_mw", "publish_time", "cutoff_time", "horizon_hours"]


def select_for_cutoff(forecasts: pd.DataFrame, targets: pd.DatetimeIndex, cutoff: pd.Timestamp) -> pd.DataFrame:
    """For each target start_time pick the vintage with max publish_time <= cutoff.

    `forecasts` has columns start_time, publish_time, generation_mw (UTC timestamps).
    Targets without an eligible vintage are omitted.
    """
    cutoff = pd.Timestamp(cutoff)
    if forecasts.empty or len(targets) == 0:
        return pd.DataFrame(columns=SELECTED_COLUMNS)
    eligible = forecasts[(forecasts["publish_time"] <= cutoff) & (forecasts["start_time"].isin(targets))]
    if eligible.empty:
        return pd.DataFrame(columns=SELECTED_COLUMNS)
    best = eligible.sort_values(["start_time", "publish_time"]).drop_duplicates("start_time", keep="last")
    out = best.rename(columns={"generation_mw": "forecast_mw"}).reset_index(drop=True)
    out["forecast_mw"] = out["forecast_mw"].astype(float)
    out["start_time"] = pd.to_datetime(out["start_time"], utc=True)
    out["publish_time"] = pd.to_datetime(out["publish_time"], utc=True)
    out["cutoff_time"] = cutoff
    out["horizon_hours"] = (out["start_time"] - out["publish_time"]).dt.total_seconds() / 3600.0
    return out[SELECTED_COLUMNS].reset_index(drop=True)


def select_for_days(
    forecasts: pd.DataFrame, start: date, end: date, cutoff_time: time, days_before: int
) -> pd.DataFrame:
    """Apply the per-delivery-day cutoff across local days start..end inclusive."""
    parts = []
    for d in iter_days(start, end):
        cutoff = pd.Timestamp(cutoff_for_day(d, cutoff_time, days_before))
        sel = select_for_cutoff(forecasts, hourly_index(d), cutoff)
        if not sel.empty:
            parts.append(sel)
    if not parts:
        return pd.DataFrame(columns=SELECTED_COLUMNS)
    return pd.concat(parts, ignore_index=True)
