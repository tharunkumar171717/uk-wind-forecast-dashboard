import math

import numpy as np
import pandas as pd
import pytest

from app.services.metrics import compute_metrics, daily_trend, error_histogram


def test_mae_rmse_bias(make_aligned):
    df = make_aligned([110, 90, 130], [100, 100, 100])  # errors 10, -10, 30
    m = compute_metrics(df)
    assert m["mae_mw"] == pytest.approx(50 / 3)
    assert m["rmse_mw"] == pytest.approx(math.sqrt((100 + 100 + 900) / 3))
    assert m["bias_mw"] == pytest.approx(10.0)
    assert m["matched_intervals"] == 3
    assert m["completeness_pct"] == 100.0


def test_wape(make_aligned):
    df = make_aligned([110, 90], [100, 300])  # |e| = 10 + 210
    assert compute_metrics(df)["wape_pct"] == pytest.approx(220 / 400 * 100)


def test_wape_zero_denominator_is_null(make_aligned):
    m = compute_metrics(make_aligned([5, 10], [0, 0]))
    assert m["wape_pct"] is None
    assert m["mae_mw"] == pytest.approx(7.5)


def test_mape_threshold_excludes_small_actuals(make_aligned):
    df = make_aligned([1100, 2400, 600], [1000, 2000, 500])
    m = compute_metrics(df, mape_min_actual_mw=1000)
    assert m["mape_intervals"] == 2
    assert m["mape_excluded_intervals"] == 1
    assert m["mape_pct"] == pytest.approx((10 + 20) / 2)


def test_mape_null_when_all_below_threshold(make_aligned):
    m = compute_metrics(make_aligned([600], [500]), mape_min_actual_mw=1000)
    assert m["mape_pct"] is None
    assert m["mape_excluded_intervals"] == 1


def test_energy_and_means(make_aligned):
    m = compute_metrics(make_aligned([1000, 3000], [2000, 2000]))
    assert m["forecast_energy_mwh"] == 4000
    assert m["actual_energy_mwh"] == 4000
    assert m["mean_forecast_mw"] == 2000


def test_empty_input():
    empty = pd.DataFrame(columns=["start_time", "forecast_mw", "actual_mw", "error_mw", "quality"])
    m = compute_metrics(empty)
    assert m["matched_intervals"] == 0
    assert m["mae_mw"] is None and m["rmse_mw"] is None and m["wape_pct"] is None
    assert m["completeness_pct"] is None
    assert error_histogram(empty) == []
    assert daily_trend(empty) == []


def test_only_matched_rows_count_and_nan_ignored(make_aligned):
    df = make_aligned([110, np.nan, 500], [100, 100, np.nan], quality=["matched", "missing_forecast", "missing_actual"])
    m = compute_metrics(df)
    assert m["matched_intervals"] == 1
    assert m["expected_intervals"] == 3
    assert m["completeness_pct"] == pytest.approx(100 / 3)
    assert m["mae_mw"] == 10
    assert m["quality_counts"] == {"matched": 1, "missing_forecast": 1, "missing_actual": 1}


def test_histogram_counts_sum(make_aligned):
    df = make_aligned([100, 700, -0.0 + 1300], [0, 0, 0])
    bins = error_histogram(df, bin_width_mw=500)
    assert sum(b["count"] for b in bins) == 3
    assert bins[0]["bin_start"] == 0
