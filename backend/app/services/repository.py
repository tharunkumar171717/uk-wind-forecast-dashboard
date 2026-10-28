"""Database access: upserts for ingestion and range reads for the API."""

from datetime import UTC, datetime

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection, Engine

from app.db import ingestion_runs, wind_actuals, wind_forecasts

BATCH_SIZE = 1000


def _py(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT or v is pd.NA:
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if hasattr(v, "item"):
        return v.item()
    return v


def _records(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    return [{c: _py(v) for c, v in zip(columns, row, strict=True)} for row in df[columns].itertuples(index=False)]


def upsert_actuals(conn: Connection, df: pd.DataFrame) -> int:
    """Insert or update half-hourly actuals. A revision only applies if its publish_time is newer or equal."""
    cols = ["start_time", "settlement_date", "settlement_period", "fuel_type", "generation_mw", "publish_time"]
    rows = _records(df, cols)
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        stmt = insert(wind_actuals).values(rows[i : i + BATCH_SIZE])
        stmt = stmt.on_conflict_do_update(
            index_elements=["start_time", "fuel_type"],
            set_={
                "generation_mw": stmt.excluded.generation_mw,
                "publish_time": stmt.excluded.publish_time,
                "settlement_date": stmt.excluded.settlement_date,
                "settlement_period": stmt.excluded.settlement_period,
                "ingested_at": func.now(),
            },
            where=(wind_actuals.c.publish_time.is_(None))
            | (stmt.excluded.publish_time >= wind_actuals.c.publish_time),
        ).returning(wind_actuals.c.id)
        # rowcount is unreliable for multi-row VALUES; RETURNING counts inserted + updated rows.
        total += len(conn.execute(stmt).all())
    return total


def upsert_forecasts(conn: Connection, df: pd.DataFrame) -> int:
    rows = _records(df, ["start_time", "publish_time", "generation_mw"])
    total = 0
    for i in range(0, len(rows), BATCH_SIZE):
        stmt = insert(wind_forecasts).values(rows[i : i + BATCH_SIZE])
        stmt = stmt.on_conflict_do_update(
            index_elements=["start_time", "publish_time"],
            set_={"generation_mw": stmt.excluded.generation_mw, "ingested_at": func.now()},
        ).returning(wind_forecasts.c.id)
        total += len(conn.execute(stmt).all())
    return total


def start_run(engine: Engine, dataset: str, window_start: datetime, window_end: datetime) -> int:
    with engine.begin() as conn:
        return conn.execute(
            insert(ingestion_runs)
            .values(dataset=dataset, status="running", window_start=window_start, window_end=window_end)
            .returning(ingestion_runs.c.id)
        ).scalar_one()


def finish_run(
    engine: Engine, run_id: int, status: str, received: int, upserted: int, rejected: int, error: str | None = None
) -> None:
    with engine.begin() as conn:
        conn.execute(
            ingestion_runs.update()
            .where(ingestion_runs.c.id == run_id)
            .values(
                status=status,
                finished_at=datetime.now(UTC),
                rows_received=received,
                rows_upserted=upserted,
                rows_rejected=rejected,
                error_message=(error or None) and error[:500],
            )
        )


class DbSource:
    """Read side used by the API."""

    mode = "live"

    def __init__(self, engine: Engine):
        self.engine = engine

    def ping(self) -> None:
        with self.engine.connect() as conn:
            conn.exec_driver_sql("select 1")

    def fetch_actuals(self, start: datetime, end: datetime) -> pd.DataFrame:
        q = select(wind_actuals.c.start_time, wind_actuals.c.generation_mw).where(
            wind_actuals.c.fuel_type == "WIND",
            wind_actuals.c.start_time >= start,
            wind_actuals.c.start_time < end,
        )
        with self.engine.connect() as conn:
            df = pd.DataFrame(conn.execute(q).all(), columns=["start_time", "generation_mw"])
        df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
        return df

    def fetch_forecasts(self, start: datetime, end: datetime, max_publish: datetime) -> pd.DataFrame:
        q = select(wind_forecasts.c.start_time, wind_forecasts.c.publish_time, wind_forecasts.c.generation_mw).where(
            wind_forecasts.c.start_time >= start,
            wind_forecasts.c.start_time < end,
            wind_forecasts.c.publish_time <= max_publish,
        )
        with self.engine.connect() as conn:
            df = pd.DataFrame(conn.execute(q).all(), columns=["start_time", "publish_time", "generation_mw"])
        df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
        df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
        return df

    def row_counts(self) -> dict:
        with self.engine.connect() as conn:
            return {
                "wind_actuals": conn.execute(select(func.count()).select_from(wind_actuals)).scalar_one(),
                "wind_forecasts": conn.execute(select(func.count()).select_from(wind_forecasts)).scalar_one(),
                "forecast_vintages": conn.execute(
                    select(func.count(func.distinct(wind_forecasts.c.publish_time)))
                ).scalar_one(),
            }

    def last_ingestion(self) -> dict:
        out = {}
        with self.engine.connect() as conn:
            for dataset in ("FUELHH", "WINDFOR"):
                row = conn.execute(
                    select(ingestion_runs.c.finished_at, ingestion_runs.c.rows_upserted)
                    .where(ingestion_runs.c.dataset == dataset, ingestion_runs.c.status == "success")
                    .order_by(ingestion_runs.c.finished_at.desc())
                    .limit(1)
                ).first()
                out[dataset] = row.finished_at if row else None
        return out
