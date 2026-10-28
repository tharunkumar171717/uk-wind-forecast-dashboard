"""CSV export of aligned intervals."""

import io

import pandas as pd

from app.services.timeutils import LONDON

CSV_COLUMNS = [
    "delivery_time_utc",
    "delivery_time_uk",
    "forecast_mw",
    "actual_mw",
    "error_mw",
    "abs_error_mw",
    "publish_time_utc",
    "cutoff_time_utc",
    "horizon_hours",
    "quality",
]


def _iso(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, utc=True)
    return s.dt.strftime("%Y-%m-%dT%H:%M:%SZ").where(s.notna(), "")


def to_csv(aligned: pd.DataFrame) -> str:
    out = pd.DataFrame(
        {
            "delivery_time_utc": _iso(aligned["start_time"]),
            "delivery_time_uk": pd.to_datetime(aligned["start_time"], utc=True)
            .dt.tz_convert(LONDON)
            .dt.strftime("%Y-%m-%d %H:%M"),
            "forecast_mw": aligned["forecast_mw"].round(1),
            "actual_mw": aligned["actual_mw"].round(1),
            "error_mw": aligned["error_mw"].round(1),
            "abs_error_mw": aligned["abs_error_mw"].round(1),
            "publish_time_utc": _iso(aligned["publish_time"]),
            "cutoff_time_utc": _iso(aligned["cutoff_time"]),
            "horizon_hours": aligned["horizon_hours"].round(2),
            "quality": aligned["quality"],
        },
        columns=CSV_COLUMNS,
    )
    buf = io.StringIO()
    out.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue()
