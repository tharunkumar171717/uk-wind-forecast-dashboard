"""HTTP API. All heavy lifting lives in the pure services; routes only validate and shape JSON."""

import math
from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.db import DatabaseNotConfigured, get_engine
from app.schemas import Accuracy, DeliveryAnalysis, ForecastDay, Health
from app.services.analysis import TTLCache, cached_analyze
from app.services.demo import DemoSource
from app.services.export import to_csv
from app.services.metrics import compute_metrics, daily_trend, error_histogram
from app.services.repository import DbSource
from app.services.timeutils import cutoff_for_day


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status, self.code, self.message = status, code, message


router = APIRouter(prefix="/api")
_cache: TTLCache | None = None


def get_cache(settings: Settings = Depends(get_settings)) -> TTLCache:
    global _cache
    if _cache is None:
        _cache = TTLCache(settings.cache_ttl_seconds)
    return _cache


def get_source(settings: Settings = Depends(get_settings)):
    if settings.data_mode == "demo":
        return DemoSource()
    try:
        return DbSource(get_engine())
    except DatabaseNotConfigured as exc:
        raise ApiError(503, "database_unavailable", "Database is not configured.") from exc


def _check_date(d: date, s: Settings) -> None:
    if not (s.eval_start <= d <= s.eval_end):
        raise ApiError(
            422, "date_out_of_range", f"Date must be between {s.eval_start} and {s.eval_end} (evaluation window)."
        )


def _check_range(start: date, end: date, s: Settings) -> None:
    if start > end:
        raise ApiError(422, "invalid_range", "start_date must be on or before end_date.")
    _check_date(start, s)
    _check_date(end, s)
    if (end - start).days + 1 > s.max_range_days:
        raise ApiError(422, "range_too_large", f"Date range may cover at most {s.max_range_days} days.")


def _clean(v):
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    return v


def _intervals(df: pd.DataFrame) -> list[dict]:
    rows = []
    for r in df.itertuples(index=False):
        rows.append(
            {
                "delivery_time": r.start_time.isoformat(),
                "forecast_mw": _clean(r.forecast_mw),
                "actual_mw": _clean(r.actual_mw),
                "error_mw": _clean(r.error_mw),
                "abs_error_mw": _clean(r.abs_error_mw),
                "publish_time": _clean(r.publish_time),
                "cutoff_time": _clean(r.cutoff_time),
                "horizon_hours": _clean(r.horizon_hours),
                "quality": r.quality,
            }
        )
    return rows


def _run(source, start: date, end: date, s: Settings, cache: TTLCache):
    try:
        return cached_analyze(
            cache, source, start, end, s.forecast_cutoff_time, s.forecast_cutoff_days_before,
            window=(s.eval_start, s.eval_end),
        )
    except SQLAlchemyError as exc:
        raise ApiError(503, "database_unavailable", "Database is unavailable. Try again later.") from exc


@router.get("/health", response_model=Health)
def health(settings: Settings = Depends(get_settings)):
    if settings.data_mode == "demo":
        return {"status": "ok", "database": "not_used", "data_mode": "demo"}
    try:
        DbSource(get_engine()).ping()
        db = "ok"
    except DatabaseNotConfigured:
        db = "not_configured"
    except Exception:
        db = "unavailable"
    return {"status": "ok" if db == "ok" else "degraded", "database": db, "data_mode": settings.data_mode}


@router.get("/metadata")
def metadata(
    settings: Settings = Depends(get_settings), source=Depends(get_source), cache: TTLCache = Depends(get_cache)
):
    key = ("metadata", source.mode)
    cached = cache.get(key)
    if cached is None:
        try:
            cached = (source.row_counts(), source.last_ingestion())
        except SQLAlchemyError as exc:
            raise ApiError(503, "database_unavailable", "Database is unavailable. Try again later.") from exc
        cache.set(key, cached)
    counts, last = cached
    finished = [v for v in last.values() if v is not None]
    return {
        "data_mode": source.mode,
        "timezone": "Europe/London",
        "evaluation_window": {"start_date": settings.eval_start.isoformat(), "end_date": settings.eval_end.isoformat()},
        "cutoff": {
            "time_local": settings.forecast_cutoff_time.strftime("%H:%M"),
            "days_before": settings.forecast_cutoff_days_before,
            "description": (
                f"Latest forecast published at or before {settings.forecast_cutoff_time.strftime('%H:%M')} "
                f"Europe/London, {settings.forecast_cutoff_days_before} day(s) before delivery."
            ),
        },
        "mape_min_actual_mw": settings.mape_min_actual_mw,
        "max_range_days": settings.max_range_days,
        "row_counts": counts,
        "last_ingestion": {k: (v.isoformat() if v else None) for k, v in last.items()},
        "last_successful_ingestion": max(finished).isoformat() if finished else None,
        "data_sources": [
            {"dataset": "FUELHH", "description": "Half-hourly outturn generation by fuel type (WIND only)",
             "endpoint": f"{settings.elexon_base_url}/datasets/FUELHH/stream"},
            {"dataset": "WINDFOR", "description": "Hourly national wind generation forecast vintages",
             "endpoint": f"{settings.elexon_base_url}/datasets/WINDFOR/stream"},
        ],
    }


@router.get("/forecasts", response_model=ForecastDay)
def forecasts(
    date_: date = Query(..., alias="date"),
    settings: Settings = Depends(get_settings),
    source=Depends(get_source),
    cache: TTLCache = Depends(get_cache),
):
    _check_date(date_, settings)
    res = _run(source, date_, date_, settings, cache)
    df = res.aligned
    pub = df["publish_time"].dropna()
    return {
        "status": "ok" if res.has_data else "no_data",
        "data_mode": source.mode,
        "date": date_.isoformat(),
        "cutoff_time": cutoff_for_day(date_, settings.forecast_cutoff_time, settings.forecast_cutoff_days_before),
        "latest_publish_time_used": pub.max().isoformat() if len(pub) else None,
        "kpis": compute_metrics(df, settings.mape_min_actual_mw),
        "series": _intervals(df) if res.has_data else [],
    }


@router.get("/accuracy", response_model=Accuracy)
def accuracy(
    start_date: date = Query(...),
    end_date: date = Query(...),
    settings: Settings = Depends(get_settings),
    source=Depends(get_source),
    cache: TTLCache = Depends(get_cache),
):
    _check_range(start_date, end_date, settings)
    res = _run(source, start_date, end_date, settings, cache)
    df = res.aligned
    return {
        "status": "ok" if res.has_data else "no_data",
        "data_mode": source.mode,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "summary": compute_metrics(df, settings.mape_min_actual_mw),
        "series": _intervals(df) if res.has_data else [],
        "daily": daily_trend(df, settings.mape_min_actual_mw) if res.has_data else [],
        "histogram": error_histogram(df),
    }


@router.get("/delivery-analysis", response_model=DeliveryAnalysis)
def delivery_analysis(
    date_: date = Query(..., alias="date"),
    settings: Settings = Depends(get_settings),
    source=Depends(get_source),
    cache: TTLCache = Depends(get_cache),
):
    _check_date(date_, settings)
    res = _run(source, date_, date_, settings, cache)
    return {
        "status": "ok" if res.has_data else "no_data",
        "data_mode": source.mode,
        "date": date_.isoformat(),
        "cutoff_time": cutoff_for_day(date_, settings.forecast_cutoff_time, settings.forecast_cutoff_days_before),
        "rows": _intervals(res.aligned) if res.has_data else [],
    }


@router.get("/export", response_class=Response)
def export(
    start_date: date = Query(...),
    end_date: date = Query(...),
    settings: Settings = Depends(get_settings),
    source=Depends(get_source),
    cache: TTLCache = Depends(get_cache),
):
    _check_range(start_date, end_date, settings)
    res = _run(source, start_date, end_date, settings, cache)
    df = res.aligned if res.has_data else res.aligned.iloc[0:0]
    suffix = "-SYNTHETIC-DEMO" if source.mode == "demo" else ""
    filename = f"wind-forecast-accuracy_{start_date}_{end_date}{suffix}.csv"
    return Response(
        content=to_csv(df),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-Data-Mode": source.mode},
    )

