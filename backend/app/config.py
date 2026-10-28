"""Application settings, loaded from environment variables / backend/.env."""

from datetime import date, time
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str | None = Field(default=None, repr=False)
    data_mode: Literal["live", "demo"] = "live"
    cors_origins: str = "http://localhost:5173"

    forecast_cutoff_time: time = time(10, 0)
    forecast_cutoff_days_before: int = Field(default=1, ge=0, le=7)

    eval_start: date = date(2026, 1, 1)
    eval_end: date = date(2026, 1, 31)
    max_range_days: int = 31

    mape_min_actual_mw: float = 1000.0
    max_valid_mw: float = 60_000.0
    cache_ttl_seconds: int = 600
    warm_cache: bool = True

    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_timeout_seconds: float = 30.0

    @field_validator("forecast_cutoff_time", mode="before")
    @classmethod
    def _parse_hhmm(cls, v):
        if isinstance(v, str) and len(v) == 5:
            return v + ":00"
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
