# Demo script

Two short videos, about 5 minutes each. Times are targets. Figures quoted are the real January 2026 results at the default cutoff (10:00 UK on D-1).

---

## Part 1: customer pitch (≤ 5 min)

**0:00 – The problem (40 s)**
"You buy power day-ahead. When you commit, you're leaning on the national wind forecast. If wind comes in lower than forecast, you're short. If it comes in higher, you've over-bought. So the useful question isn't how good the forecast is in general. It's how good the forecast was **at the moment you had to decide**."

**0:40 – Overview page (90 s)**
- Pick 15 Jan 2026. Point out the label "Retrospective comparison: forecast as of cutoff vs actual outturn".
- Cutoff panel: "We only use forecasts published by 10:00 UK the day before. Here the latest one we were allowed to see was published at 09:30 on the 14th, so the horizons run from 14.5 to 37.5 hours."
- Chart: hover a point to show forecast, actual, error and publish time.
- KPI cards: "On this day the forecast averaged 11,678 MW against 10,568 MW actual. Average miss (MAE) was 1,110 MW, all in one direction: bias +1,110 MW."
- "How to read errors" box: positive error means less wind than expected.

**2:10 – Accuracy page, all of January (80 s)**
- MAE 2,123 MW: "the typical size of a miss in an hour."
- RMSE 2,617 MW: "higher than MAE because some misses are large. Plan for the tail, not the average."
- Bias +1,840 MW: "the forecast ran high almost all month. A buyer using it unadjusted would usually have expected more wind than arrived."
- WAPE 18.3%: "about 18% of wind volume, in error terms."
- Histogram: the distribution sits right of zero. Daily chart: the worst days stand out at once.

**3:30 – Delivery-day table and export (30 s)**
Sort by |error|, filter by quality, export CSV for your own analysis.

**4:00 – Honest limitations (50 s)**
- The 10:00 D-1 cutoff is our **assumption** about decision time, not a market rule. It's configurable, and a later cutoff gives lower error (about 1,970 MW MAE at 16:00).
- The "actual" is metered transmission wind after curtailment. Part of the +1.8 GW bias may be that definitional gap, not forecasting skill.
- One winter month. This is a retrospective tool, not a price or volume optimiser.

---

## Part 2: technical review (≤ 5 min)

**0:00 – Architecture (40 s)**
Show the Mermaid diagram in the README: Elexon → `app.ingest` → Supabase Postgres → FastAPI → React. The frontend only talks to FastAPI. Secrets live in `backend/.env` and in the Render env, never in the repo.

**0:40 – Ingestion (50 s)**
- `services/elexon.py`: stream endpoints, retries with exponential backoff on 429 and 5xx, WINDFOR in ≤1-day publish windows.
- `services/validation.py`: rejects NaN, negative and > 60 GW rows (never zero-filled).
- Upserts use `ON CONFLICT`. For actuals, the latest `publish_time` wins. Every run is logged in `ingestion_runs`.
- January load: 1,584 actuals and 18,980 forecast rows across 260 vintages, re-runnable.

**1:30 – Vintage selection and alignment (70 s)**
- `services/selection.py`: per delivery day, max `publish_time ≤ cutoff(D)`, with each day using its own cutoff.
- `services/timeutils.py`: Europe/London bounds via `zoneinfo`.
- `services/alignment.py`: hourly actual = mean of HH:00 and HH:30, joined on timestamp, with quality flags.
- Show the tests: exactly-at-cutoff is included and +1 s is excluded, DST days have 23 and 25 h, and joins are by timestamp not position.

**2:40 – Metrics and API (50 s)**
- `services/metrics.py` holds pure functions (WAPE is null for a zero denominator, MAPE has a threshold and reports exclusions).
- `api/routes.py`: errors use a consistent `{"error": {...}}` shape, with 422, 503 and `no_data`.
- The whole window is analysed once, cached for 10 minutes, and each request is sliced from it (a test proves the slice equals a direct computation). Show `/docs`.

**3:30 – Tests, Docker, deploy (50 s)**
- `pytest`: 44 pass, including Postgres integration against `postgres:16`. `npm test`: 10 pass.
- `docker compose up --build`: db, backend (non-root, healthcheck) and frontend (nginx proxying `/api`).
- `backend/vercel.json` (Sydney region) and `frontend/vercel.json` (SPA rewrite); secrets only in Vercel settings.

**4:20 – Trade-offs and next steps (40 s)**
- An in-process cache is fine for a single instance. Use Redis or materialised tables to scale out.
- Next steps:
  - a scheduled ingestion job;
  - a cutoff selector in the UI;
  - error by horizon bucket;
  - more months;
  - comparing against embedded-inclusive outturn to separate bias from definition.

---

## Recording checklist (unlisted YouTube)

- [ ] Backend warm (hit `/api/health` and one page first, so the first load is fast).
- [ ] Browser at 1440×900, zoom 100%, no other tabs or bookmarks visible, notifications off.
- [ ] Nothing secret on screen: no `.env`, no Supabase dashboard, no terminal history with URIs.
- [ ] Record Part 1 and Part 2 separately. Each must be 5 minutes or less.
- [ ] Check audio level and that the mouse cursor is visible when hovering tooltips.
- [ ] Upload to YouTube with visibility set to **Unlisted**. Add the title and a short description with the repo link.
- [ ] Open the link in a private window to confirm it plays while signed out.
- [ ] Only then add the link to the README.

The video has **not** been recorded or uploaded yet.
