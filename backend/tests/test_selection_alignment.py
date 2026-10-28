from datetime import date, time

import numpy as np
import pandas as pd

from app.services.alignment import align, hourly_actuals
from app.services.selection import select_for_cutoff, select_for_days
from app.services.timeutils import cutoff_for_day, hourly_index, local_day_bounds

T = pd.Timestamp


def fc(rows):
    return pd.DataFrame(
        [{"start_time": T(s), "publish_time": T(p), "generation_mw": g} for s, p, g in rows]
    )


def test_cutoff_boundary_inclusive_and_one_second_after_excluded():
    target = pd.DatetimeIndex([T("2026-01-15T12:00Z")])
    cutoff = T("2026-01-14T10:00:00Z")
    df = fc(
        [
            ("2026-01-15T12:00Z", "2026-01-14T07:30:00Z", 100),
            ("2026-01-15T12:00Z", "2026-01-14T10:00:00Z", 200),  # exactly at cutoff -> included
            ("2026-01-15T12:00Z", "2026-01-14T10:00:01Z", 999),  # 1 s after -> excluded
        ]
    )
    sel = select_for_cutoff(df, target, cutoff)
    assert sel["forecast_mw"].tolist() == [200]
    assert sel["publish_time"].iloc[0] == T("2026-01-14T10:00:00Z")
    assert sel["horizon_hours"].iloc[0] == 26.0
    assert sel["cutoff_time"].iloc[0] == cutoff


def test_latest_vintage_wins_and_duplicates_ok():
    target = pd.DatetimeIndex([T("2026-01-15T00:00Z")])
    df = fc(
        [
            ("2026-01-15T00:00Z", "2026-01-13T09:30Z", 1),
            ("2026-01-15T00:00Z", "2026-01-14T04:30Z", 2),
            ("2026-01-15T00:00Z", "2026-01-14T04:30Z", 2),
            ("2026-01-15T00:00Z", "2026-01-14T09:30Z", 3),
        ]
    )
    assert select_for_cutoff(df, target, T("2026-01-14T10:00Z"))["forecast_mw"].tolist() == [3]


def test_no_eligible_vintage_gives_empty():
    df = fc([("2026-01-15T00:00Z", "2026-01-14T11:30Z", 5)])
    assert select_for_cutoff(df, pd.DatetimeIndex([T("2026-01-15T00:00Z")]), T("2026-01-14T10:00Z")).empty


def test_cutoff_uses_london_time_in_summer():
    # 10:00 BST on 2026-06-30 = 09:00 UTC
    assert cutoff_for_day(date(2026, 7, 1), time(10), 1) == T("2026-06-30T09:00Z")
    assert cutoff_for_day(date(2026, 1, 15), time(10), 1) == T("2026-01-14T10:00Z")


def test_select_for_days_uses_each_days_own_cutoff():
    df = fc(
        [
            ("2026-01-15T23:00Z", "2026-01-14T09:30Z", 10),
            ("2026-01-16T00:00Z", "2026-01-14T09:30Z", 20),
            ("2026-01-16T00:00Z", "2026-01-15T09:30Z", 30),  # allowed for day 16 (cutoff 15th 10:00)
            ("2026-01-15T23:00Z", "2026-01-15T09:30Z", 99),  # after day 15's cutoff -> must not leak
        ]
    )
    sel = select_for_days(df, date(2026, 1, 15), date(2026, 1, 16), time(10), 1).set_index("start_time")
    assert sel.loc[T("2026-01-15T23:00Z"), "forecast_mw"] == 10
    assert sel.loc[T("2026-01-16T00:00Z"), "forecast_mw"] == 30


def test_dst_day_lengths():
    for d, hours in [(date(2026, 3, 29), 23), (date(2026, 10, 25), 25), (date(2026, 1, 15), 24)]:
        lo, hi = local_day_bounds(d)
        assert (hi - lo).total_seconds() / 3600 == hours
        assert len(hourly_index(d)) == hours
    lo, _ = local_day_bounds(date(2026, 7, 1))
    assert lo == T("2026-06-30T23:00Z")


def _actuals(rows):
    return pd.DataFrame([{"start_time": T(s), "generation_mw": g} for s, g in rows])


def test_half_hour_to_hour_mean():
    h = hourly_actuals(_actuals([("2026-01-15T00:00Z", 100), ("2026-01-15T00:30Z", 200)]))
    assert h["actual_mw"].tolist() == [150]
    assert h["halves"].tolist() == [2]


def test_align_quality_flags():
    targets = pd.date_range("2026-01-15T00:00Z", periods=5, freq="h")
    selected = pd.DataFrame(
        {
            "start_time": [targets[0], targets[1], targets[2]],
            "forecast_mw": [180.0, 50.0, 70.0],
            "publish_time": T("2026-01-14T09:30Z"),
            "cutoff_time": T("2026-01-14T10:00Z"),
            "horizon_hours": [14.5, 15.5, 16.5],
        }
    )
    actuals = _actuals(
        [
            ("2026-01-15T00:00Z", 100), ("2026-01-15T00:30Z", 200),  # h0 full -> matched
            ("2026-01-15T01:00Z", 100),                               # h1 one half -> partial
            # h2 none -> missing_actual
            ("2026-01-15T03:00Z", 10), ("2026-01-15T03:30Z", 20),    # h3 no forecast -> missing_forecast
            # h4 nothing -> missing_both
        ]
    )
    df = align(selected, actuals, targets)
    assert df["quality"].tolist() == ["matched", "partial_actual", "missing_actual", "missing_forecast", "missing_both"]
    assert df.loc[0, "error_mw"] == 30
    assert df.loc[0, "abs_error_mw"] == 30
    assert np.isnan(df.loc[1, "error_mw"]) and np.isnan(df.loc[1, "actual_mw"])
    assert df.loc[3, "actual_mw"] == 15


def test_align_by_timestamp_not_position():
    targets = pd.date_range("2026-01-15T00:00Z", periods=2, freq="h")
    selected = pd.DataFrame(
        {"start_time": [targets[1], targets[0]], "forecast_mw": [2000.0, 1000.0],
         "publish_time": T("2026-01-14T09:30Z"), "cutoff_time": T("2026-01-14T10:00Z"), "horizon_hours": [1.0, 2.0]}
    )
    actuals = _actuals([("2026-01-15T01:30Z", 1900), ("2026-01-15T01:00Z", 1900),
                        ("2026-01-15T00:30Z", 900), ("2026-01-15T00:00Z", 900)])
    df = align(selected, actuals, targets)
    assert df["error_mw"].tolist() == [100, 100]


def test_align_empty_inputs():
    targets = hourly_index(date(2026, 1, 15))
    df = align(pd.DataFrame(), pd.DataFrame(columns=["start_time", "generation_mw"]), targets)
    assert len(df) == 24
    assert set(df["quality"]) == {"missing_both"}
