"""Accuracy metrics over matched intervals. error = forecast - actual."""

import math

import numpy as np
import pandas as pd

from app.services.timeutils import LONDON


def _f(x) -> float | None:
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else x


def compute_metrics(aligned: pd.DataFrame, mape_min_actual_mw: float = 1000.0) -> dict:
    """Summary metrics. Only rows flagged `matched` count towards error metrics."""
    expected = int(len(aligned))
    m = aligned[aligned["quality"] == "matched"] if expected else aligned
    f = m["forecast_mw"].to_numpy(dtype=float) if len(m) else np.array([])
    a = m["actual_mw"].to_numpy(dtype=float) if len(m) else np.array([])
    keep = np.isfinite(f) & np.isfinite(a)
    f, a = f[keep], a[keep]
    e = f - a
    n = int(len(e))

    sum_abs_actual = float(np.abs(a).sum()) if n else 0.0
    mape_mask = a >= mape_min_actual_mw
    mape_n = int(mape_mask.sum())

    return {
        "matched_intervals": n,
        "expected_intervals": expected,
        "completeness_pct": _f(n / expected * 100) if expected else None,
        "mae_mw": _f(np.mean(np.abs(e))) if n else None,
        "rmse_mw": _f(np.sqrt(np.mean(e**2))) if n else None,
        "bias_mw": _f(np.mean(e)) if n else None,
        "wape_pct": _f(np.abs(e).sum() / sum_abs_actual * 100) if n and sum_abs_actual > 0 else None,
        "mape_pct": _f(np.mean(np.abs(e[mape_mask]) / a[mape_mask]) * 100) if mape_n else None,
        "mape_min_actual_mw": mape_min_actual_mw,
        "mape_intervals": mape_n,
        "mape_excluded_intervals": n - mape_n,
        "mean_forecast_mw": _f(f.mean()) if n else None,
        "mean_actual_mw": _f(a.mean()) if n else None,
        # Hourly average MW x 1 h = MWh.
        "forecast_energy_mwh": _f(f.sum()) if n else None,
        "actual_energy_mwh": _f(a.sum()) if n else None,
        "quality_counts": aligned["quality"].value_counts().to_dict() if expected else {},
    }


def error_histogram(aligned: pd.DataFrame, bin_width_mw: float = 500.0) -> list[dict]:
    e = aligned.loc[aligned["quality"] == "matched", "error_mw"].dropna().to_numpy(dtype=float)
    if len(e) == 0:
        return []
    lo = math.floor(e.min() / bin_width_mw) * bin_width_mw
    hi = math.floor(e.max() / bin_width_mw) * bin_width_mw + bin_width_mw
    edges = np.arange(lo, hi + bin_width_mw / 2, bin_width_mw)
    counts, edges = np.histogram(e, bins=edges)
    return [
        {"bin_start": float(edges[i]), "bin_end": float(edges[i + 1]), "count": int(counts[i])}
        for i in range(len(counts))
    ]


def daily_trend(aligned: pd.DataFrame, mape_min_actual_mw: float = 1000.0) -> list[dict]:
    if aligned.empty:
        return []
    df = aligned.copy()
    df["date"] = df["start_time"].dt.tz_convert(LONDON).dt.date
    out = []
    for d, grp in df.groupby("date", sort=True):
        m = compute_metrics(grp, mape_min_actual_mw)
        out.append(
            {
                "date": d.isoformat(),
                "mae_mw": m["mae_mw"],
                "rmse_mw": m["rmse_mw"],
                "bias_mw": m["bias_mw"],
                "matched_intervals": m["matched_intervals"],
                "expected_intervals": m["expected_intervals"],
            }
        )
    return out
