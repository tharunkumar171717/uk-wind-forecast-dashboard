"""SQLAlchemy engine and table definitions (mirroring migrations/001_init.sql)."""

from functools import lru_cache

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    SmallInteger,
    Table,
    Text,
    create_engine,
)
from sqlalchemy.engine import Engine

from app.config import get_settings

metadata = MetaData()

wind_actuals = Table(
    "wind_actuals",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("settlement_date", Date),
    Column("settlement_period", SmallInteger),
    Column("fuel_type", Text, nullable=False),
    Column("generation_mw", Float, nullable=False),
    Column("publish_time", DateTime(timezone=True)),
    Column("ingested_at", DateTime(timezone=True)),
)

wind_forecasts = Table(
    "wind_forecasts",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("start_time", DateTime(timezone=True), nullable=False),
    Column("publish_time", DateTime(timezone=True), nullable=False),
    Column("generation_mw", Float, nullable=False),
    Column("ingested_at", DateTime(timezone=True)),
)

ingestion_runs = Table(
    "ingestion_runs",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("dataset", Text, nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    Column("status", Text),
    Column("rows_received", Integer),
    Column("rows_upserted", Integer),
    Column("rows_rejected", Integer),
    Column("window_start", DateTime(timezone=True)),
    Column("window_end", DateTime(timezone=True)),
    Column("error_message", Text),
)


class DatabaseNotConfigured(RuntimeError):
    pass


def _sqlalchemy_url(url: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def make_engine(url: str) -> Engine:
    return create_engine(
        _sqlalchemy_url(url),
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=3,
        pool_recycle=300,
        # prepare_threshold=None disables server-side prepared statements, which keeps
        # the engine compatible with Supabase's transaction pooler (port 6543) too.
        connect_args={"connect_timeout": 5, "prepare_threshold": None},
    )


@lru_cache
def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise DatabaseNotConfigured("DATABASE_URL is not set")
    return make_engine(url)
