import os

# Tests never touch a real database unless TEST_DATABASE_URL is set explicitly.
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("DATA_MODE", "live")
os.environ["WARM_CACHE"] = "false"

import pandas as pd
import pytest


def aligned_frame(forecast, actual, quality=None):
    """Build an aligned-like frame for metric tests."""
    n = len(forecast)
    f = pd.Series(forecast, dtype=float)
    a = pd.Series(actual, dtype=float)
    q = quality or ["matched"] * n
    e = (f - a).where(pd.Series(q) == "matched")
    return pd.DataFrame(
        {
            "start_time": pd.date_range("2026-01-15", periods=n, freq="h", tz="UTC"),
            "forecast_mw": f,
            "actual_mw": a,
            "error_mw": e,
            "abs_error_mw": e.abs(),
            "publish_time": pd.Timestamp("2026-01-14T09:30Z"),
            "cutoff_time": pd.Timestamp("2026-01-14T10:00Z"),
            "horizon_hours": 15.0,
            "quality": q,
        }
    )


@pytest.fixture
def make_aligned():
    return aligned_frame
