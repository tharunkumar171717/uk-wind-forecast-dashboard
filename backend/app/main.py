"""FastAPI application entrypoint: uvicorn app.main:app"""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import ApiError, get_cache, get_source, metadata, router
from app.config import get_settings
from app.services.analysis import cached_analyze

log = logging.getLogger("app")


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _warm_cache() -> None:
    """Load the evaluation window into the cache so the first page view is fast."""
    s = get_settings()
    try:
        metadata(s, get_source(s), get_cache(s))
        cached_analyze(
            get_cache(s), get_source(s), s.eval_start, s.eval_end, s.forecast_cutoff_time,
            s.forecast_cutoff_days_before, window=(s.eval_start, s.eval_end),
        )
        log.info("cache warmed")
    except Exception as exc:  # DB may be down at boot; requests will retry.
        log.warning("cache warm-up skipped: %s", type(exc).__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().warm_cache:
        threading.Thread(target=_warm_cache, daemon=True).start()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        lifespan=lifespan,
        title="UK Wind Forecast Accuracy API",
        version="1.0.0",
        description="Decision-time national wind forecast (Elexon WINDFOR) vs actual outturn (Elexon FUELHH).",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Data-Mode"],
    )
    app.include_router(router)

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return _error(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError):
        parts = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []) if x != "query")
            parts.append(f"{loc}: {err.get('msg')}")
        return _error(422, "invalid_parameter", "; ".join(parts) or "Invalid request parameters.")

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException):
        return _error(exc.status_code, "not_found" if exc.status_code == 404 else "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        # Log the type only: exception messages from DB drivers can contain connection details.
        log.error("unhandled error: %s", type(exc).__name__)
        return _error(500, "internal_error", "Unexpected server error.")

    @app.get("/", include_in_schema=False)
    def root():
        return {"name": "UK Wind Forecast Accuracy API", "docs": "/docs", "health": "/api/health"}

    return app


app = create_app()
