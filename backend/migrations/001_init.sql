-- UK wind forecast accuracy: initial schema. Idempotent; safe to re-run.

CREATE TABLE IF NOT EXISTS wind_actuals (
    id                bigserial PRIMARY KEY,
    start_time        timestamptz NOT NULL,
    settlement_date   date,
    settlement_period smallint,
    fuel_type         text NOT NULL DEFAULT 'WIND',
    generation_mw     double precision NOT NULL CHECK (generation_mw >= 0),
    publish_time      timestamptz,
    ingested_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (start_time, fuel_type)
);
CREATE INDEX IF NOT EXISTS wind_actuals_start_time_idx ON wind_actuals (start_time);

CREATE TABLE IF NOT EXISTS wind_forecasts (
    id            bigserial PRIMARY KEY,
    start_time    timestamptz NOT NULL,
    publish_time  timestamptz NOT NULL,
    generation_mw double precision NOT NULL CHECK (generation_mw >= 0),
    ingested_at   timestamptz NOT NULL DEFAULT now(),
    UNIQUE (start_time, publish_time)
);
CREATE INDEX IF NOT EXISTS wind_forecasts_start_time_idx ON wind_forecasts (start_time);
CREATE INDEX IF NOT EXISTS wind_forecasts_publish_time_idx ON wind_forecasts (publish_time);
CREATE INDEX IF NOT EXISTS wind_forecasts_start_publish_desc_idx ON wind_forecasts (start_time, publish_time DESC);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id             bigserial PRIMARY KEY,
    dataset        text NOT NULL,
    started_at     timestamptz NOT NULL DEFAULT now(),
    finished_at    timestamptz,
    status         text NOT NULL DEFAULT 'running',
    rows_received  integer NOT NULL DEFAULT 0,
    rows_upserted  integer NOT NULL DEFAULT 0,
    rows_rejected  integer NOT NULL DEFAULT 0,
    window_start   timestamptz,
    window_end     timestamptz,
    error_message  text
);
CREATE INDEX IF NOT EXISTS ingestion_runs_dataset_finished_idx ON ingestion_runs (dataset, finished_at DESC);

-- Row Level Security with no policies: the anon/authenticated API roles get nothing.
-- The backend connects as the table owner via DATABASE_URL.
ALTER TABLE wind_actuals ENABLE ROW LEVEL SECURITY;
ALTER TABLE wind_forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_runs ENABLE ROW LEVEL SECURITY;
