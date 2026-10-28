"""Validate raw Elexon rows into clean DataFrames. Invalid rows are rejected, never zero-filled."""

from dataclasses import dataclass

import numpy as np
import pandas as pd

MAX_VALID_MW = 60_000.0

ACTUAL_COLUMNS = ["start_time", "settlement_date", "settlement_period", "fuel_type", "generation_mw", "publish_time"]
FORECAST_COLUMNS = ["start_time", "publish_time", "generation_mw"]


@dataclass
class ValidationResult:
    frame: pd.DataFrame
    received: int
    rejected: int


def _to_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True, errors="coerce")


def _valid_generation(series: pd.Series, max_mw: float) -> tuple[pd.Series, pd.Series]:
    gen = pd.to_numeric(series, errors="coerce").astype(float)
    ok = gen.notna() & np.isfinite(gen) & (gen >= 0) & (gen <= max_mw)
    return gen, ok


def validate_actuals(records: list[dict], max_mw: float = MAX_VALID_MW) -> ValidationResult:
    """FUELHH rows -> one row per (start_time) WIND half-hour; latest publishTime wins."""
    received = len(records)
    if not records:
        return ValidationResult(pd.DataFrame(columns=ACTUAL_COLUMNS), 0, 0)
    raw = pd.DataFrame.from_records(records)
    for col in ("startTime", "publishTime", "generation", "fuelType", "settlementDate", "settlementPeriod"):
        if col not in raw:
            raw[col] = None

    df = pd.DataFrame(
        {
            "start_time": _to_utc(raw["startTime"]),
            "publish_time": _to_utc(raw["publishTime"]),
            "settlement_date": pd.to_datetime(raw["settlementDate"], errors="coerce").dt.date,
            "settlement_period": pd.to_numeric(raw["settlementPeriod"], errors="coerce"),
            "fuel_type": raw["fuelType"].astype("string").str.upper(),
        }
    )
    df["generation_mw"], gen_ok = _valid_generation(raw["generation"], max_mw)
    ok = gen_ok & df["start_time"].notna() & (df["fuel_type"] == "WIND")
    # Settlement periods must be on the half-hour.
    ok &= (df["start_time"].dt.minute.isin([0, 30])) & (df["start_time"].dt.second == 0)
    df = df[ok.fillna(False)].copy()

    df = df.sort_values(["start_time", "publish_time"], na_position="first")
    df = df.drop_duplicates(subset=["start_time"], keep="last")
    df["settlement_period"] = df["settlement_period"].astype("Int64")
    df["fuel_type"] = df["fuel_type"].astype(str)
    df = df[ACTUAL_COLUMNS].reset_index(drop=True)
    return ValidationResult(df, received, received - len(df))


def validate_forecasts(records: list[dict], max_mw: float = MAX_VALID_MW) -> ValidationResult:
    """WINDFOR rows -> one row per (start_time, publish_time) vintage."""
    received = len(records)
    if not records:
        return ValidationResult(pd.DataFrame(columns=FORECAST_COLUMNS), 0, 0)
    raw = pd.DataFrame.from_records(records)
    for col in ("startTime", "publishTime", "generation"):
        if col not in raw:
            raw[col] = None

    df = pd.DataFrame({"start_time": _to_utc(raw["startTime"]), "publish_time": _to_utc(raw["publishTime"])})
    df["generation_mw"], gen_ok = _valid_generation(raw["generation"], max_mw)
    ok = gen_ok & df["start_time"].notna() & df["publish_time"].notna()
    df = df[ok.fillna(False)].copy()
    # Exact duplicates of a vintage row: keep the last one received.
    df = df.drop_duplicates(subset=["start_time", "publish_time"], keep="last")
    df = df.sort_values(["start_time", "publish_time"])[FORECAST_COLUMNS].reset_index(drop=True)
    return ValidationResult(df, received, received - len(df))
