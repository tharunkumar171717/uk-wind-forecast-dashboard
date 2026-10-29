# UK Wind Power Forecast Accuracy Dashboard

How good was Great Britain's national wind generation forecast **at the moment a day-ahead buying decision was made**? This app answers that for January 2026. It takes the forecast that was actually available before a decision cutoff, compares it with metered wind outturn, and shows the size and direction of the errors.

All data is public Elexon (BMRS) data: **WINDFOR** for forecasts and **FUELHH** for wind outturn. The scope is national wind only. There is no demand, price, solar or financial-impact modelling.

> **Live app / repo / video:** see [Deployment status](#deployment-status). Only verified URLs are listed there.

---

## Features

- **Overview**: pick a delivery day and see KPI cards (forecast energy, average forecast and actual MW, MAE, bias, matched hours and completeness), the cutoff used, the latest publish time used, the horizon range, and a forecast-vs-actual chart. The tooltip shows delivery time (UK), forecast, actual, error and publish time.
- **Forecast Accuracy**: pick a date range and see MAE, RMSE, bias, WAPE and MAPE (with its threshold note), forecast vs actual over time, absolute error over time, an error histogram, and daily MAE and bias.
- **Delivery-Day Analysis**: an hourly table with sorting, a quality filter, pagination, and CSV export through the backend.
- **Methodology & Data Quality**: datasets, the cutoff rule, formulas, missing-data rules, timezone handling, limitations, and live ingestion status.
- Every page has loading, empty ("No data yet: run ingestion") and error states.
- **Demo mode** (`DATA_MODE=demo`) serves deterministic synthetic data, labelled everywhere: `data_mode: "demo"` in the API, a yellow banner in the UI, and `-SYNTHETIC-DEMO` in CSV filenames.

## Tools we used and why

| Tool | Used for | Why |
|---|---|---|
| **React** | The website screens | Builds pages from small reusable parts. Its virtual DOM updates only the part of the page that changed, so it stays fast. |
| **Vite** | Running and building the React app | Very fast start-up and build. |
| **Tailwind CSS** | Look and style | Quick to style, and every page looks the same. |
| **Recharts** | Charts | Made for React, with hover boxes built in. |
| **React Router** | Moving between the 4 pages | Changes page without a full reload. |
| **Python + FastAPI** | The backend (API) | Fast and simple. It checks inputs for us and makes the `/docs` page by itself. |
| **pandas + numpy** | Maths on the data | The standard tools for tables of numbers: matching hours, working out errors. |
| **httpx** | Downloading data from Elexon | Simple, with timeouts and retries. |
| **Supabase (PostgreSQL)** | Storing the data | A ready online Postgres database on a free plan, with no server to manage. We save the Elexon data once instead of downloading it on every visit. |
| **SQLAlchemy + psycopg** | Talking to the database from Python | The standard, safe way to run queries. |
| **Docker** | Running everything together | One command starts the database, backend and website the same way on any computer. |
| **Vercel** | Putting it online | Free plan, and it deploys from GitHub automatically. |
| **Pytest + Vitest** | Tests | The standard test tools for Python and React. |

## Results on real data (January 2026, cutoff 10:00 UK on D-1)

| Matched hours | MAE | RMSE | Bias | WAPE | MAPE (actual ≥ 1,000 MW) |
|---|---|---|---|---|---|
| 744 / 744 (100%) | 2,123 MW | 2,617 MW | **+1,840 MW** | 18.3% | 22.1% (0 hours excluded) |

Mean forecast was 13,421 MW against a mean actual of 11,581 MW. The forecast was **consistently above** metered outturn. See [Limitations](#limitations) for why part of this gap may be a definitional difference rather than forecast skill.

## Architecture

```mermaid
flowchart LR
  E[Elexon Insights API<br/>FUELHH + WINDFOR] -->|python -m app.ingest<br/>validate + upsert| S[(Supabase Postgres<br/>wind_actuals, wind_forecasts,<br/>ingestion_runs)]
  S -->|SQLAlchemy / psycopg 3| A[FastAPI backend<br/>selection, alignment, metrics<br/>+ TTL cache]
  A -->|JSON / CSV| R[React + Vite SPA<br/>Tailwind, Recharts]
```

- The frontend talks **only** to FastAPI. It never sees Supabase keys or the connection string.
- `selection`, `alignment`, `metrics` and `export` are pure pandas/numpy functions with no DB or HTTP access, so they are deterministic and unit-tested.
- The API analyses the whole evaluation window once, caches it in memory (TTL 10 min, warmed at startup), and slices each request from the cache. This is valid because forecast selection is independent per delivery day. A test checks that a sliced day equals a directly computed day.

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, error handlers, CORS, cache warm-up
│   │   ├── config.py          # pydantic-settings
│   │   ├── db.py              # engine + table definitions
│   │   ├── ingest.py          # python -m app.ingest
│   │   ├── migrate.py         # python -m app.migrate
│   │   ├── api/routes.py      # endpoints + param validation
│   │   ├── schemas/           # response models (OpenAPI)
│   │   └── services/          # elexon, validation, selection, alignment, metrics,
│   │                          # repository, analysis, export, timeutils, demo
│   ├── migrations/001_init.sql
│   ├── tests/                 # pytest (unit, API, Postgres integration)
│   ├── Dockerfile, requirements.txt, requirements-dev.txt, .env.example
├── frontend/
│   ├── src/{api,hooks,components,pages,utils,test}
│   ├── Dockerfile, nginx.conf, vercel.json, .env.example
├── docs/demo-script.md
└── docker-compose.yml
```

## Elexon data

Base URL `https://data.elexon.co.uk/bmrs/api/v1`. No API key is needed. Both endpoints were checked with real calls on 2026-10-28.

| Dataset | Request | Shape |
|---|---|---|
| FUELHH (actuals) | `GET /datasets/FUELHH/stream?settlementDateFrom=…&settlementDateTo=…&fuelType=WIND` | Half-hourly MW per settlement period (48/day; 46/50 on clock-change days). `startTime` is UTC. |
| WINDFOR (forecasts) | `GET /datasets/WINDFOR/stream?publishDateTimeFrom=…Z&publishDateTimeTo=…Z` | Hourly MW. A new vintage roughly every 2–3 h (e.g. 02:30, 04:30, 07:30, 09:30, 11:30Z), each about 73 hours long. |

How ingestion works:
- FUELHH is fetched for settlement dates from start−1 to end+1, in 7-day chunks.
- WINDFOR is fetched in **≤1-day publish windows** from start−3 days to the last cutoff.
- 429, 5xx and network errors retry with exponential backoff, honouring `Retry-After`.
- Empty responses are valid.

**January 2026 load (actually run against Supabase):** 1,584 actual half-hours and 18,980 forecast rows across 260 vintages, with 0 rows rejected. A second run upserted the same rows and left table totals unchanged, which shows ingestion is idempotent.

## Forecast selection (no leakage)

- **Delivery days** are Europe/London calendar days. All timestamps are stored as UTC `timestamptz`, and `zoneinfo` gives DST-correct bounds (29 Mar 2026 = 23 h, 25 Oct 2026 = 25 h).
- **Cutoff(D)** = `FORECAST_CUTOFF_TIME` Europe/London on D − `FORECAST_CUTOFF_DAYS_BEFORE` (default **10:00 on D-1**). **This is an assumption** modelled on GB day-ahead auction timing. It is **not** an official Elexon rule.
- For each hourly interval of D, the selected vintage has the **largest `publish_time` ≤ cutoff(D)**:
  - Anything published after the cutoff is ignored, even by one second (this is tested).
  - Actuals never influence the choice.
  - Each day uses its own cutoff.
- Every vintage is stored, so any cutoff can be replayed. Each interval returns `publish_time`, `cutoff_time` and `horizon_hours`.

### How the cutoff changes the results (real January 2026 data)

| Cutoff | Matched | Horizon (mean) | MAE | RMSE | Bias | WAPE |
|---|---|---|---|---|---|---|
| 10:00 D-2 | 682 / 744 | 38.5–59.5 h (49.0) | 2,550 | 3,094 | +1,990 | 22.1% |
| 06:00 D-1 | 744 | 19.5–42.5 h (31.0) | 2,139 | 2,637 | +1,798 | 18.5% |
| **10:00 D-1 (default)** | 744 | 14.5–37.5 h (26.0) | **2,123** | **2,617** | **+1,840** | **18.3%** |
| 16:00 D-1 | 744 | 8.5–37.5 h (20.2) | 1,966 | 2,430 | +1,802 | 17.0% |

What the table shows:
- A **later cutoff** means shorter horizons and lower error.
- An **earlier cutoff** (D-2) misses some hours entirely, because vintages only reach about 3 days ahead. Those hours are flagged `missing_forecast`.
- Bias barely moves with the cutoff. A roughly constant +1.8 GW offset points to a systematic difference rather than horizon-driven error.

## Alignment and data-quality rules

- Forecasts are hourly and actuals are half-hourly. **Hourly actual = mean of the HH:00 and HH:30 periods**, because both are average MW. Rows are joined **by timestamp**, never by row position.
- Quality flags per hour:

  | Flag | Meaning |
  |---|---|
  | `matched` | Forecast present and both half-hours present. Only these hours count in metrics. |
  | `partial_actual` | Forecast present, one half-hour missing. Excluded from metrics. |
  | `missing_actual` | Forecast present, no actual. |
  | `missing_forecast` | No eligible forecast, but there is an actual. |
  | `missing_both` | Neither. |

- Validation rejects rows with:
  - NaN or non-numeric values
  - negative values
  - absurd values (> 60,000 MW)
  - unparseable timestamps
  - a fuel type other than WIND
  - FUELHH start times not on a :00 or :30 boundary

  Rejected rows are **never treated as zero**.
- Duplicates and revisions:
  - Exact duplicate forecast rows are collapsed.
  - Multiple vintages are all kept.
  - For revised actuals, the latest `publishTime` wins, both in validation and in the DB upsert (`… DO UPDATE … WHERE excluded.publish_time >= existing`).

## Metrics

Metrics use matched intervals only, with **error = forecast − actual**.

| Metric | Formula | Reading |
|---|---|---|
| MAE | mean(\|e\|) | Typical size of a miss (MW) |
| RMSE | √mean(e²) | Like MAE, but big misses weigh more |
| Bias | mean(e) | **+** means over-forecast (less wind than expected); **−** means under-forecast |
| WAPE | Σ\|e\| / Σ\|actual\| × 100 | Volume-weighted % error. Null when Σ\|actual\| = 0 |
| MAPE | mean(\|e\| / actual) × 100 where actual ≥ `MAPE_MIN_ACTUAL_MW` (1,000) | Excluded hours are reported |
| Energy | Σ hourly MW × 1 h | MWh |
| Completeness | matched / expected hours | Uses DST-aware expected hours |

## Limitations

- FUELHH "WIND" is metered output from transmission-connected (BM) wind. It is **after curtailment** and excludes most embedded (distribution-connected) wind. WINDFOR may not measure exactly the same quantity, so part of the persistent positive bias may be definitional or caused by curtailment rather than forecast error. This app does not try to correct for that.
- The 10:00 D-1 cutoff is an assumption, not a market rule. It is configurable.
- One winter month only. Seasonal behaviour is not covered.
- This is a retrospective view only. It does not model purchase volumes, prices or financial impact (out of scope by design).

## Local setup

Prerequisites: Python 3.12, Node 20+ (tested with 26), and optionally Docker and `psql`.

```bash
# Backend
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env            # then put your DATABASE_URL in .env
.venv/bin/python -m app.migrate
.venv/bin/python -m app.ingest --start 2026-01-01 --end 2026-01-31
.venv/bin/uvicorn app.main:app --reload --port 8000   # http://localhost:8000/docs

# Frontend (new terminal); Vite proxies /api to :8000
cd frontend
npm ci
npm run dev                     # http://localhost:5173
```

To run without any database, set `DATA_MODE=demo` in `backend/.env`. You get synthetic, clearly labelled data.

### Supabase setup

1. Supabase dashboard → **Connect** → **Session pooler**. Copy the URI (`postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`) and add `?sslmode=require`.
   - The Transaction pooler (port 6543) also works, because the engine disables prepared statements (`prepare_threshold=None`).
2. Put it in `backend/.env` as `DATABASE_URL=…`. This file is git-ignored.
3. Run `python -m app.migrate`. It is idempotent: it creates the tables and indexes and enables RLS with **no** policies, so the anon and authenticated API roles can read nothing. The backend connects as the table owner.
4. Run `python -m app.ingest --start 2026-01-01 --end 2026-01-31`. It is safe to re-run, and every run is recorded in `ingestion_runs`.

## Docker

```bash
docker compose up --build
# frontend http://localhost:8080 (nginx proxies /api to the backend)
# backend  http://localhost:8000/docs
# db       local postgres:16 on localhost:5433 (user/pass/db: wind)
```

- `backend` reads `backend/.env`, so it uses Supabase by default. To use the local db instead, set `DATABASE_URL=postgresql://wind:wind@db:5432/wind`, then run migrate and ingest inside the container: `docker compose exec backend python -m app.migrate`.
- Images:
  - The backend runs as non-root uid 10001 with a `HEALTHCHECK` on `/api/health`.
  - The frontend is a multi-stage Node build served by nginx.
  - `.env` is excluded from the build context by `.dockerignore`.
- Verified locally: all three services came up (db and backend healthy). `/api/health` returned `{"status":"ok","database":"ok","data_mode":"live"}` both directly and through nginx, and the SPA routes returned 200.

## Tests

```bash
cd backend
.venv/bin/python -m pytest                       # 41 pass, 3 skip (Postgres tests)
docker compose up -d db
TEST_DATABASE_URL=postgresql://wind:wind@localhost:5433/wind .venv/bin/python -m pytest   # 44 pass

cd frontend && npm test                          # 10 pass
```

Backend coverage:
- Metrics: MAE, RMSE, bias, WAPE (including a zero denominator), MAPE threshold exclusion, empty input and NaN.
- Selection: cutoff boundary (published exactly at cutoff is included; one second later is excluded), latest vintage wins, no leakage across days.
- Time: Europe/London bounds, including the 23 h and 25 h DST days.
- Alignment: half-hour → hour, quality flags, joining by timestamp not position.
- Validation and the Elexon client: retries, give-up, ≤1-day windows.
- API: 422 for bad parameters, 503 on DB failure without leaking details, `no_data` for an empty DB, CSV headers and content, the CORS allow-list, and the sliced cache equalling a direct computation.
- Postgres integration: upsert idempotency and the latest-publish rule.

Frontend coverage: KpiCard and the loading, error, empty and demo states, plus pages rendered with a mocked API.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | App status plus DB connectivity (`ok` / `degraded`) |
| `GET /api/metadata` | Cutoff config, evaluation window, row counts, last ingestion, sources, data mode |
| `GET /api/forecasts?date=2026-01-15` | Day series, KPIs, cutoff, latest publish time used |
| `GET /api/accuracy?start_date=…&end_date=…` | Summary metrics, hourly series, daily trend, histogram |
| `GET /api/delivery-analysis?date=…` | Table rows |
| `GET /api/export?start_date=…&end_date=…` | CSV download |

Rules shared by all endpoints:
- Errors always look like `{"error": {"code", "message"}}`.
- Bad parameters return **422**: invalid date, start > end, outside 2026-01-01..2026-01-31, or more than 31 days.
- A database outage returns **503** `database_unavailable`, with no stack traces or connection details.
- An empty DB returns **200** with `"status": "no_data"`.
- CORS allows only the `CORS_ORIGINS` list.
- OpenAPI docs are at `/docs`.

## Environment variables

**Backend** (`backend/.env` locally; on Vercel, set them in the backend project's Environment Variables)

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | none | Supabase Session pooler URI with `?sslmode=require`. **Secret.** |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `FORECAST_CUTOFF_TIME` | `10:00` | Europe/London local time |
| `FORECAST_CUTOFF_DAYS_BEFORE` | `1` | Days before delivery |
| `DATA_MODE` | `live` | `demo` serves labelled synthetic data |
| `MAPE_MIN_ACTUAL_MW` | `1000` | MAPE threshold |
| `CACHE_TTL_SECONDS` | `600` | In-memory cache TTL |
| `WARM_CACHE` | `true` | Pre-load the evaluation window at startup (set `false` on Vercel) |

**Frontend** (`frontend/.env`, or Vercel project env)

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | Backend origin, e.g. `https://uk-wind-forecast-api.vercel.app`. Leave empty for same-origin `/api` (dev proxy or nginx). Not secret. |

## Deployment

Both parts run on Vercel, as two projects from this one repo.

**Backend on Vercel** (FastAPI as a Vercel Function).
1. Import the repo with root directory `backend`. Vercel finds `app` in `app/main.py`.
2. `backend/vercel.json` sets the region to Sydney (`syd1`), next to the Supabase database, and `maxDuration` to 60 s.
3. Set `DATABASE_URL` (secret), `CORS_ORIGINS=https://<frontend>.vercel.app`, `WARM_CACHE=false` and the cutoff variables.
4. `.vercelignore` keeps `.env`, tests and the virtualenv out of the upload.

**Frontend on Vercel.**
1. Import the repo with root directory `frontend` and framework Vite.
2. Set `VITE_API_BASE_URL=https://<backend>.vercel.app`.
3. `vercel.json` adds the SPA rewrite.

### Deployment status

<!-- Only URLs that were verified with real requests are listed here. -->
| What | URL | Verified (2026-10-29) |
|---|---|---|
| Live app (Vercel) | https://uk-wind-forecast-dashboard-two.vercel.app | `/`, `/accuracy`, `/delivery`, `/methodology` return 200 |
| API (Vercel, Sydney) | https://uk-wind-forecast-api.vercel.app | `/api/health` gives `{"status":"ok","database":"ok","data_mode":"live"}`; January MAE 2,122.8 MW over 744 matched hours (same as local); CSV export works; CORS allows only the app's origin |
| API docs | https://uk-wind-forecast-api.vercel.app/docs | 200 |
| Repository | https://github.com/tharunkumar171717/uk-wind-forecast-dashboard | public |
| Demo video | not recorded yet | |

The frontend Vercel project is linked to this repo (root directory `frontend`) and deploys on every push to `main`. The backend Vercel project is deployed from the `backend` folder with `vercel deploy --prod`.

## AI tools disclosure

This project was built with **Claude Code** (Anthropic's Claude, Opus 5.5) acting as a coding agent from a written build prompt. The agent:
- wrote the code, tests, Docker and deploy config, and this README;
- ran the Elexon checks, ingestion, tests and Docker build shown above, and reported their real output.

A human (the repo owner) supplied the requirements, credentials and accounts, and is responsible for reviewing the result. No other AI tools were used.
