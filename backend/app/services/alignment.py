"""Align hourly forecasts with half-hourly actuals by timestamp and assign quality flags."""

import numpy as np
import pandas as pd

MATCHED = "matched"
MISSING_FORECAST = "missing_forecast"
MISSING_ACTUAL = "missing_actual"
PARTIAL_ACTUAL = "partial_actual"
MISSING_BOTH = "missing_both"
QUALITY_FLAGS = [MATCHED, MISSING_FORECAST, MISSING_ACTUAL, PARTIAL_ACTUAL, MISSING_BOTH]

ALIGNED_COLUMNS = [
    "start_time",
    "forecast_mw",
    "actual_mw",
    "error_mw",
    "abs_error_mw",
    "publish_time",
    "cutoff_time",
    "horizon_hours",
    "quality",
]


def hourly_actuals(actuals: pd.DataFrame) -> pd.DataFrame:
    """Half-hourly MW -> hourly mean of the HH:00 and HH:30 periods.

    Returns columns start_time, actual_mw, halves (number of half-hours present).
    Hours with only one half-hour get actual_mw = NaN (partial).
    """
    if actuals.empty:
        return pd.DataFrame(columns=["start_time", "actual_mw", "halves"])
    a = actuals[["start_time", "generation_mw"]].dropna().copy()
    a["start_time"] = pd.to_datetime(a["start_time"], utc=True)
    a = a.drop_duplicates("start_time", keep="last")
    a["hour"] = a["start_time"].dt.floor("h")
    g = a.groupby("hour")["generation_mw"].agg(["mean", "count"]).reset_index()
    g.columns = ["start_time", "actual_mw", "halves"]
    g.loc[g["halves"] < 2, "actual_mw"] = np.nan
    return g


def align(selected: pd.DataFrame, actuals: pd.DataFrame, targets: pd.DatetimeIndex) -> pd.DataFrame:
    """One row per target hour with forecast, actual, error and a quality flag.

    error = forecast - actual, only for `matched` rows.
    """
    base = pd.DataFrame({"start_time": targets})
    sel = selected.copy()
    if not sel.empty:
        sel["start_time"] = pd.to_datetime(sel["start_time"], utc=True)
    else:
        sel = pd.DataFrame(columns=["start_time", "forecast_mw", "publish_time", "cutoff_time", "horizon_hours"])
        sel["start_time"] = pd.to_datetime(sel["start_time"], utc=True)
    hourly = hourly_actuals(actuals)
    if hourly.empty:
        hourly["start_time"] = pd.to_datetime(hourly["start_time"], utc=True)

    df = base.merge(sel, on="start_time", how="left").merge(hourly, on="start_time", how="left")
    df["forecast_mw"] = pd.to_numeric(df["forecast_mw"], errors="coerce").astype(float)
    df["actual_mw"] = pd.to_numeric(df["actual_mw"], errors="coerce").astype(float)
    df["halves"] = pd.to_numeric(df["halves"], errors="coerce").fillna(0).astype(int)
    df["horizon_hours"] = pd.to_numeric(df["horizon_hours"], errors="coerce").astype(float)

    has_f = df["forecast_mw"].notna()
    full_a = df["halves"] >= 2
    any_a = df["halves"] >= 1
    df["quality"] = np.select(
        [has_f & full_a, has_f & any_a, has_f, full_a],
        [MATCHED, PARTIAL_ACTUAL, MISSING_ACTUAL, MISSING_FORECAST],
        default=MISSING_BOTH,
    )
    matched = df["quality"] == MATCHED
    df["error_mw"] = np.where(matched, df["forecast_mw"] - df["actual_mw"], np.nan)
    df["abs_error_mw"] = df["error_mw"].abs()
    return df[ALIGNED_COLUMNS].reset_index(drop=True)
