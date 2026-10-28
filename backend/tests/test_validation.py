import httpx
import pandas as pd
import pytest

from app.services.elexon import ElexonClient, ElexonError
from app.services.validation import validate_actuals, validate_forecasts


def fuel(start, gen, pub="2026-01-15T01:00:00Z", fuel_type="WIND"):
    return {"dataset": "FUELHH", "publishTime": pub, "startTime": start, "settlementDate": "2026-01-15",
            "settlementPeriod": 1, "fuelType": fuel_type, "generation": gen}


def test_actuals_rejects_bad_rows():
    rows = [
        fuel("2026-01-15T00:00:00Z", 1000),
        fuel("2026-01-15T00:30:00Z", -5),          # negative
        fuel("2026-01-15T01:00:00Z", 75_000),      # absurd
        fuel("2026-01-15T01:30:00Z", None),        # missing
        fuel("2026-01-15T02:00:00Z", "NaN"),       # NaN
        fuel("not-a-date", 10),                    # bad timestamp
        fuel("2026-01-15T02:30:00Z", 10, fuel_type="CCGT"),
        fuel("2026-01-15T03:10:00Z", 10),          # not on a settlement boundary
    ]
    r = validate_actuals(rows)
    assert r.received == 8
    assert r.rejected == 7
    assert r.frame["generation_mw"].tolist() == [1000.0]


def test_actuals_latest_publish_wins():
    rows = [
        fuel("2026-01-15T00:00:00Z", 1000, pub="2026-01-15T01:00:00Z"),
        fuel("2026-01-15T00:00:00Z", 1100, pub="2026-01-15T03:00:00Z"),
        fuel("2026-01-15T00:00:00Z", 900, pub="2026-01-15T02:00:00Z"),
    ]
    r = validate_actuals(rows)
    assert r.frame["generation_mw"].tolist() == [1100.0]
    assert r.frame["publish_time"].iloc[0] == pd.Timestamp("2026-01-15T03:00:00Z")


def test_forecasts_keep_all_vintages_drop_exact_dupes():
    rows = [
        {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-14T04:30:00Z", "generation": 1},
        {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-14T09:30:00Z", "generation": 2},
        {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-14T09:30:00Z", "generation": 3},
        {"startTime": "2026-01-15T00:00:00Z", "publishTime": None, "generation": 3},
    ]
    r = validate_forecasts(rows)
    assert len(r.frame) == 2
    assert r.rejected == 2
    assert r.frame["generation_mw"].tolist() == [1.0, 3.0]


def test_empty_payloads():
    assert validate_actuals([]).frame.empty
    assert validate_forecasts([]).frame.empty


def test_elexon_client_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429 if calls["n"] == 1 else 503)
        return httpx.Response(200, json=[{"startTime": "x"}])

    with ElexonClient(transport=httpx.MockTransport(handler), backoff_base=0) as c:
        rows = c.fetch_windfor(pd.Timestamp("2026-01-01T00:00Z"), pd.Timestamp("2026-01-01T12:00Z"))
    assert rows == [{"startTime": "x"}]
    assert calls["n"] == 3


def test_elexon_client_gives_up():
    with ElexonClient(transport=httpx.MockTransport(lambda r: httpx.Response(500)), max_retries=1, backoff_base=0) as c:
        with pytest.raises(ElexonError):
            c.fetch_fuelhh_wind(pd.Timestamp("2026-01-01").date(), pd.Timestamp("2026-01-01").date())


def test_windfor_windows_are_at_most_one_day():
    seen = []

    def handler(request):
        seen.append((request.url.params["publishDateTimeFrom"], request.url.params["publishDateTimeTo"]))
        return httpx.Response(200, json=[])

    with ElexonClient(transport=httpx.MockTransport(handler)) as c:
        assert c.fetch_windfor(pd.Timestamp("2026-01-01T00:00Z"), pd.Timestamp("2026-01-03T10:00Z")) == []
    assert seen == [
        ("2026-01-01T00:00:00Z", "2026-01-01T23:59:59Z"),
        ("2026-01-02T00:00:00Z", "2026-01-02T23:59:59Z"),
        ("2026-01-03T00:00:00Z", "2026-01-03T10:00:00Z"),
    ]
