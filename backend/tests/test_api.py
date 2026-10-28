import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api import routes
from app.main import app
from app.services.analysis import TTLCache


class FakeSource:
    mode = "live"

    def __init__(self, actuals=None, forecasts=None, fail=False):
        self.actuals = actuals if actuals is not None else pd.DataFrame(columns=["start_time", "generation_mw"])
        self.forecasts = (
            forecasts if forecasts is not None else pd.DataFrame(columns=["start_time", "publish_time", "generation_mw"])
        )
        self.fail = fail

    def _maybe_fail(self):
        if self.fail:
            raise OperationalError("select 1", {}, Exception("connection refused"))

    def ping(self):
        self._maybe_fail()

    def fetch_actuals(self, start, end):
        self._maybe_fail()
        a = self.actuals
        return a[(a["start_time"] >= start) & (a["start_time"] < end)]

    def fetch_forecasts(self, start, end, max_publish):
        self._maybe_fail()
        f = self.forecasts
        return f[(f["start_time"] >= start) & (f["start_time"] < end) & (f["publish_time"] <= max_publish)]

    def row_counts(self):
        self._maybe_fail()
        return {"wind_actuals": len(self.actuals), "wind_forecasts": len(self.forecasts), "forecast_vintages": 0}

    def last_ingestion(self):
        self._maybe_fail()
        return {"FUELHH": None, "WINDFOR": None}


def one_day_source():
    hours = pd.date_range("2026-01-15T00:00Z", periods=24, freq="h")
    halves = pd.date_range("2026-01-15T00:00Z", periods=48, freq="30min")
    actuals = pd.DataFrame({"start_time": halves, "generation_mw": 1000.0})
    forecasts = pd.concat(
        [
            pd.DataFrame({"start_time": hours, "publish_time": pd.Timestamp("2026-01-14T09:30Z"), "generation_mw": 1100.0}),
            # Published after the cutoff: must never be used.
            pd.DataFrame({"start_time": hours, "publish_time": pd.Timestamp("2026-01-14T11:30Z"), "generation_mw": 5000.0}),
        ]
    )
    return FakeSource(actuals, forecasts)


@pytest.fixture
def client():
    def _make(source):
        app.dependency_overrides[routes.get_source] = lambda: source
        app.dependency_overrides[routes.get_cache] = lambda: TTLCache(0)
        return TestClient(app, raise_server_exceptions=False)

    yield _make
    app.dependency_overrides.clear()


def test_forecasts_ok(client):
    r = client(one_day_source()).get("/api/forecasts", params={"date": "2026-01-15"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["cutoff_time"] == "2026-01-14T10:00:00Z"
    assert body["latest_publish_time_used"].startswith("2026-01-14T09:30:00")
    assert len(body["series"]) == 24
    assert body["kpis"]["mae_mw"] == 100
    assert body["kpis"]["bias_mw"] == 100
    s0 = body["series"][0]
    assert s0["horizon_hours"] == 14.5 and s0["quality"] == "matched"


@pytest.mark.parametrize(
    "path,params,code",
    [
        ("/api/forecasts", {"date": "15-01-2026"}, "invalid_parameter"),
        ("/api/forecasts", {}, "invalid_parameter"),
        ("/api/forecasts", {"date": "2025-12-31"}, "date_out_of_range"),
        ("/api/accuracy", {"start_date": "2026-01-10", "end_date": "2026-01-01"}, "invalid_range"),
        ("/api/accuracy", {"start_date": "2026-01-01", "end_date": "2026-02-05"}, "date_out_of_range"),
        ("/api/export", {"start_date": "2026-01-01"}, "invalid_parameter"),
    ],
)
def test_param_validation_422(client, path, params, code):
    r = client(FakeSource()).get(path, params=params)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == code
    assert "message" in r.json()["error"]


def test_range_too_large(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "max_range_days", 5)
    r = client(FakeSource()).get("/api/accuracy", params={"start_date": "2026-01-01", "end_date": "2026-01-10"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "range_too_large"


def test_db_failure_returns_503_without_details(client):
    c = client(FakeSource(fail=True))
    for path, params in [
        ("/api/forecasts", {"date": "2026-01-15"}),
        ("/api/accuracy", {"start_date": "2026-01-01", "end_date": "2026-01-31"}),
        ("/api/metadata", {}),
    ]:
        r = c.get(path, params=params)
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "database_unavailable"
        assert "connection refused" not in r.text and "postgres" not in r.text.lower()


def test_db_not_configured_returns_503():
    # conftest blanks DATABASE_URL, so the real dependency must refuse cleanly.
    app.dependency_overrides.clear()
    r = TestClient(app).get("/api/forecasts", params={"date": "2026-01-15"})
    assert r.status_code == 503
    assert r.json() == {"error": {"code": "database_unavailable", "message": "Database is not configured."}}


def test_health_degraded_without_db():
    r = TestClient(app).get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"


def test_empty_db_returns_no_data(client):
    c = client(FakeSource())
    r = c.get("/api/accuracy", params={"start_date": "2026-01-01", "end_date": "2026-01-31"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "no_data"
    assert body["series"] == [] and body["daily"] == [] and body["histogram"] == []
    r = c.get("/api/delivery-analysis", params={"date": "2026-01-15"})
    assert r.json()["status"] == "no_data" and r.json()["rows"] == []


def test_export_csv(client):
    r = client(one_day_source()).get("/api/export", params={"start_date": "2026-01-15", "end_date": "2026-01-15"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert 'filename="wind-forecast-accuracy_2026-01-15_2026-01-15.csv"' in r.headers["content-disposition"]
    lines = r.text.strip().split("\n")
    assert lines[0] == (
        "delivery_time_utc,delivery_time_uk,forecast_mw,actual_mw,error_mw,abs_error_mw,"
        "publish_time_utc,cutoff_time_utc,horizon_hours,quality"
    )
    assert len(lines) == 25
    assert lines[1] == (
        "2026-01-15T00:00:00Z,2026-01-15 00:00,1100.0,1000.0,100.0,100.0,"
        "2026-01-14T09:30:00Z,2026-01-14T10:00:00Z,14.5,matched"
    )


def test_cors_only_allows_configured_origin(client):
    c = client(FakeSource())
    ok = c.get("/api/health", headers={"Origin": "http://localhost:5173"})
    bad = c.get("/api/health", headers={"Origin": "https://evil.example"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


def test_single_day_sliced_from_cached_window_matches_direct(client):
    """The per-day view sliced from the cached January analysis equals a direct one-day analysis."""
    from app.services.analysis import analyze, cached_analyze
    from datetime import date, time

    src = one_day_source()
    cache = TTLCache(60)
    sliced = cached_analyze(cache, src, date(2026, 1, 15), date(2026, 1, 15), time(10), 1,
                            window=(date(2026, 1, 1), date(2026, 1, 31)))
    direct = analyze(src, date(2026, 1, 15), date(2026, 1, 15), time(10), 1)
    pd.testing.assert_frame_equal(sliced.aligned, direct.aligned)
    assert sliced.has_data and direct.has_data
    empty_day = cached_analyze(cache, src, date(2026, 1, 3), date(2026, 1, 3), time(10), 1,
                               window=(date(2026, 1, 1), date(2026, 1, 31)))
    assert not empty_day.has_data
