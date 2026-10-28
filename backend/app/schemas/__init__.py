"""Response models (used for validation and the OpenAPI docs)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable", "not_configured", "not_used"]
    data_mode: Literal["live", "demo"]


class Interval(BaseModel):
    delivery_time: datetime
    forecast_mw: float | None
    actual_mw: float | None
    error_mw: float | None
    abs_error_mw: float | None
    publish_time: datetime | None
    cutoff_time: datetime | None
    horizon_hours: float | None
    quality: str


class Metrics(BaseModel):
    matched_intervals: int
    expected_intervals: int
    completeness_pct: float | None
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    wape_pct: float | None
    mape_pct: float | None
    mape_min_actual_mw: float
    mape_intervals: int
    mape_excluded_intervals: int
    mean_forecast_mw: float | None
    mean_actual_mw: float | None
    forecast_energy_mwh: float | None
    actual_energy_mwh: float | None
    quality_counts: dict[str, int]


class DailyPoint(BaseModel):
    date: str
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    matched_intervals: int
    expected_intervals: int


class HistogramBin(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class ForecastDay(BaseModel):
    status: Literal["ok", "no_data"]
    data_mode: Literal["live", "demo"]
    date: str
    cutoff_time: datetime
    latest_publish_time_used: datetime | None
    kpis: Metrics
    series: list[Interval]


class Accuracy(BaseModel):
    status: Literal["ok", "no_data"]
    data_mode: Literal["live", "demo"]
    start_date: str
    end_date: str
    summary: Metrics
    series: list[Interval]
    daily: list[DailyPoint]
    histogram: list[HistogramBin]


class DeliveryAnalysis(BaseModel):
    status: Literal["ok", "no_data"]
    data_mode: Literal["live", "demo"]
    date: str
    cutoff_time: datetime
    rows: list[Interval]
