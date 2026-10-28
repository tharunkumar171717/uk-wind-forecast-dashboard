"""Elexon Insights (BMRS) API client with retries and backoff. No API key required."""

import logging
import time as _time
from datetime import date, datetime, timedelta

import httpx

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}


class ElexonError(RuntimeError):
    pass


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class ElexonClient:
    def __init__(
        self,
        base_url: str = "https://data.elexon.co.uk/bmrs/api/v1",
        timeout: float = 30.0,
        max_retries: int = 5,
        backoff_base: float = 1.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._client = httpx.Client(
            base_url=base_url, timeout=timeout, transport=transport, headers={"Accept": "application/json"}
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def _get(self, path: str, params: dict) -> list[dict]:
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._client.get(path, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == self.max_retries:
                    raise ElexonError(f"{path}: network error after retries: {exc}") from exc
                self._sleep(attempt, None)
                continue
            if resp.status_code in RETRY_STATUS and attempt < self.max_retries:
                self._sleep(attempt, resp.headers.get("Retry-After"))
                continue
            if resp.status_code != 200:
                raise ElexonError(f"{path}: HTTP {resp.status_code}")
            body = resp.json()
            # /stream endpoints return a bare list; non-stream endpoints wrap rows in {"data": [...]}.
            if isinstance(body, dict):
                body = body.get("data", [])
            if not isinstance(body, list):
                raise ElexonError(f"{path}: unexpected payload type {type(body).__name__}")
            return body
        raise ElexonError(f"{path}: exhausted retries")

    def _sleep(self, attempt: int, retry_after: str | None) -> None:
        delay = self.backoff_base * (2**attempt)
        if retry_after and retry_after.isdigit():
            delay = max(delay, float(retry_after))
        log.warning("Elexon retry %s in %.1fs", attempt + 1, delay)
        _time.sleep(min(delay, 60))

    def fetch_fuelhh_wind(self, date_from: date, date_to: date, chunk_days: int = 7) -> list[dict]:
        """FUELHH WIND rows for settlement dates date_from..date_to inclusive."""
        rows: list[dict] = []
        d = date_from
        while d <= date_to:
            chunk_end = min(d + timedelta(days=chunk_days - 1), date_to)
            rows += self._get(
                "/datasets/FUELHH/stream",
                {"settlementDateFrom": d.isoformat(), "settlementDateTo": chunk_end.isoformat(), "fuelType": "WIND"},
            )
            d = chunk_end + timedelta(days=1)
        return rows

    def fetch_windfor(self, publish_from: datetime, publish_to: datetime) -> list[dict]:
        """WINDFOR rows with publishTime in [publish_from, publish_to], fetched in <=1-day windows."""
        rows: list[dict] = []
        lo = publish_from
        while lo <= publish_to:
            hi = min(lo + timedelta(days=1) - timedelta(seconds=1), publish_to)
            rows += self._get(
                "/datasets/WINDFOR/stream",
                {"publishDateTimeFrom": _iso(lo), "publishDateTimeTo": _iso(hi)},
            )
            lo = hi + timedelta(seconds=1)
        return rows
