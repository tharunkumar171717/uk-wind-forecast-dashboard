"""Ingest Elexon FUELHH (wind actuals) and WINDFOR (wind forecasts) into Postgres.

Usage: python -m app.ingest --start 2026-01-01 --end 2026-01-31

Safe to re-run: every write is an upsert.
"""

import argparse
import logging
import sys
from datetime import UTC, date, datetime, time, timedelta

from app.config import get_settings
from app.db import get_engine
from app.services import repository
from app.services.elexon import ElexonClient
from app.services.timeutils import cutoff_for_day
from app.services.validation import validate_actuals, validate_forecasts


def _ingest(engine, dataset: str, window_start: datetime, window_end: datetime, fetch, validate, upsert, max_mw):
    run_id = repository.start_run(engine, dataset, window_start, window_end)
    try:
        result = validate(fetch(), max_mw)
        with engine.begin() as conn:
            upserted = upsert(conn, result.frame)
        repository.finish_run(engine, run_id, "success", result.received, upserted, result.rejected)
        return {"dataset": dataset, "received": result.received, "valid": len(result.frame),
                "upserted": upserted, "rejected": result.rejected}
    except Exception as exc:
        repository.finish_run(engine, run_id, "failed", 0, 0, 0, f"{type(exc).__name__}: {exc}")
        raise


def run(start: date, end: date) -> list[dict]:
    settings = get_settings()
    engine = get_engine()
    summaries = []
    with ElexonClient(settings.elexon_base_url, settings.elexon_timeout_seconds) as client:
        a_from, a_to = start - timedelta(days=1), end + timedelta(days=1)
        summaries.append(
            _ingest(
                engine, "FUELHH",
                datetime.combine(a_from, time(0), tzinfo=UTC), datetime.combine(a_to, time(23, 59), tzinfo=UTC),
                lambda: client.fetch_fuelhh_wind(a_from, a_to),
                validate_actuals, repository.upsert_actuals, settings.max_valid_mw,
            )
        )
        f_from = datetime.combine(start - timedelta(days=3), time(0), tzinfo=UTC)
        f_to = cutoff_for_day(end, settings.forecast_cutoff_time, settings.forecast_cutoff_days_before)
        summaries.append(
            _ingest(
                engine, "WINDFOR", f_from, f_to,
                lambda: client.fetch_windfor(f_from, f_to),
                validate_forecasts, repository.upsert_forecasts, settings.max_valid_mw,
            )
        )
    return summaries


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--start", type=date.fromisoformat, default=date(2026, 1, 1))
    p.add_argument("--end", type=date.fromisoformat, default=date(2026, 1, 31))
    args = p.parse_args(argv)
    if args.start > args.end:
        p.error("--start must be <= --end")
    for s in run(args.start, args.end):
        print(
            f"{s['dataset']:8} received={s['received']} valid={s['valid']} "
            f"upserted={s['upserted']} rejected={s['rejected']}"
        )
    counts = repository.DbSource(get_engine()).row_counts()
    print("table totals:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
