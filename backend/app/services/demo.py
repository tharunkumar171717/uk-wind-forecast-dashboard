"""Deterministic SYNTHETIC data for DATA_MODE=demo. Not Elexon data; never mixed with real data."""

from datetime import UTC, datetime, timedelta
from functools import lru_cache

import numpy as np
import pandas as pd

_START = datetime(2025, 12, 27, tzinfo=UTC)
_END = datetime(2026, 2, 2, tzinfo=UTC)


@lru_cache(maxsize=1)
def _synthetic() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(20260101)
    half_hours = pd.date_range(_START, _END, freq="30min", inclusive="left", tz="UTC")
    t = np.arange(len(half_hours)) / 48.0  # days
    walk = np.cumsum(rng.normal(0, 250, len(t)))
    walk -= np.linspace(walk[0], walk[-1], len(t))
    actual = 12_000 + 5_500 * np.sin(2 * np.pi * t / 6.5) + 1_200 * np.sin(2 * np.pi * t) + walk
    actual = np.clip(actual, 400, 22_000)
    actuals = pd.DataFrame({"start_time": half_hours, "generation_mw": actual.round(0)})

    hourly = actuals.set_index("start_time")["generation_mw"].resample("h").mean()
    vintages = []
    publish = _START + timedelta(hours=2, minutes=30)
    while publish < _END:
        targets = pd.date_range(pd.Timestamp(publish).ceil("h"), periods=72, freq="h", tz="UTC")
        targets = targets[targets < _END]
        horizon = (targets - pd.Timestamp(publish)).total_seconds().to_numpy() / 3600
        truth = hourly.reindex(targets).to_numpy()
        # Error grows with horizon, plus a small positive bias.
        noise = rng.normal(0, 1, len(targets)).cumsum() * 60
        f = truth + noise * np.sqrt(horizon / 24 + 0.2) + 300
        vintages.append(pd.DataFrame({"start_time": targets, "publish_time": pd.Timestamp(publish),
                                      "generation_mw": np.clip(f, 0, 25_000).round(0)}))
        publish += timedelta(hours=3)
    forecasts = pd.concat(vintages, ignore_index=True)
    return actuals, forecasts


class DemoSource:
    mode = "demo"

    def ping(self) -> None:
        return None

    def fetch_actuals(self, start: datetime, end: datetime) -> pd.DataFrame:
        a, _ = _synthetic()
        return a[(a["start_time"] >= start) & (a["start_time"] < end)].reset_index(drop=True)

    def fetch_forecasts(self, start: datetime, end: datetime, max_publish: datetime) -> pd.DataFrame:
        _, f = _synthetic()
        m = (f["start_time"] >= start) & (f["start_time"] < end) & (f["publish_time"] <= max_publish)
        return f[m].reset_index(drop=True)

    def row_counts(self) -> dict:
        a, f = _synthetic()
        return {"wind_actuals": len(a), "wind_forecasts": len(f), "forecast_vintages": int(f["publish_time"].nunique())}

    def last_ingestion(self) -> dict:
        return {"FUELHH": None, "WINDFOR": None}
