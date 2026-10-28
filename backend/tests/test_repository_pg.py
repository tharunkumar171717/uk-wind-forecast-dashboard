"""Integration tests against a real Postgres. Run with TEST_DATABASE_URL pointing at a throwaway DB,
e.g. the docker compose `db` service: TEST_DATABASE_URL=postgresql://wind:wind@localhost:5433/wind_test
"""

import os

import pandas as pd
import pytest
from sqlalchemy import text

from app.db import make_engine
from app.migrate import apply_migrations
from app.services import repository
from app.services.validation import validate_actuals, validate_forecasts

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def engine():
    eng = make_engine(URL)
    apply_migrations(eng)
    apply_migrations(eng)  # migrations are idempotent
    with eng.begin() as conn:
        conn.execute(text("TRUNCATE wind_actuals, wind_forecasts, ingestion_runs RESTART IDENTITY"))
    yield eng
    eng.dispose()


def _actual_rows(gen, pub):
    return [
        {"publishTime": pub, "startTime": f"2026-01-15T00:{m:02d}:00Z", "settlementDate": "2026-01-15",
         "settlementPeriod": i + 1, "fuelType": "WIND", "generation": gen}
        for i, m in enumerate((0, 30))
    ]


def test_upsert_actuals_idempotent_and_latest_publish_wins(engine):
    first = validate_actuals(_actual_rows(1000, "2026-01-15T01:00:00Z")).frame
    with engine.begin() as conn:
        assert repository.upsert_actuals(conn, first) == 2
    with engine.begin() as conn:
        repository.upsert_actuals(conn, first)  # re-run: no duplicates
    newer = validate_actuals(_actual_rows(1200, "2026-01-15T05:00:00Z")).frame
    older = validate_actuals(_actual_rows(1, "2026-01-15T00:45:00Z")).frame
    with engine.begin() as conn:
        repository.upsert_actuals(conn, newer)
        assert repository.upsert_actuals(conn, older) == 0  # stale revision ignored
    with engine.connect() as conn:
        rows = conn.execute(text("select generation_mw from wind_actuals order by start_time")).scalars().all()
    assert rows == [1200, 1200]


def test_upsert_forecasts_idempotent_and_read_back(engine):
    rows = [
        {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-14T04:30:00Z", "generation": 10},
        {"startTime": "2026-01-15T00:00:00Z", "publishTime": "2026-01-14T09:30:00Z", "generation": 20},
    ]
    df = validate_forecasts(rows).frame
    for _ in range(3):
        with engine.begin() as conn:
            repository.upsert_forecasts(conn, df)
    src = repository.DbSource(engine)
    assert src.row_counts() == {"wind_actuals": 0, "wind_forecasts": 2, "forecast_vintages": 2}
    got = src.fetch_forecasts(
        pd.Timestamp("2026-01-15T00:00Z"), pd.Timestamp("2026-01-16T00:00Z"), pd.Timestamp("2026-01-14T06:00Z")
    )
    assert got["generation_mw"].tolist() == [10]


def test_ingestion_run_recorded(engine):
    run_id = repository.start_run(engine, "FUELHH", pd.Timestamp("2026-01-01T00:00Z"), pd.Timestamp("2026-01-02T00:00Z"))
    repository.finish_run(engine, run_id, "success", 10, 9, 1)
    last = repository.DbSource(engine).last_ingestion()
    assert last["FUELHH"] is not None and last["WINDFOR"] is None
