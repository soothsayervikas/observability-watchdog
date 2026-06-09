import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.api.deps import init_db
from app.api.v1.router import create_api_router
from app.config import get_settings
from app.core.exceptions import (
    AnalysisInProgressError,
    ConfigurationError,
    IngestionError,
    IngestionParseError,
    WatchdogError,
    WebhookDeliveryError,
)
from app.core.http_client import close_http_client
from app.core.logging import configure_logging, get_logger, request_id_var
from app.core.metrics import record_http_request, render_prometheus
from app.core.rate_limit import RateLimitMiddleware
from app.middleware.auth import ApiKeyAuthMiddleware
from app.middleware.security import RequestBodySizeLimitMiddleware, SecurityHeadersMiddleware

logger = get_logger(__name__)


def _prune_expired_logs() -> None:
    from datetime import timedelta

    from app.api.deps import SessionLocal, build_services
    from app.core.datetime_utils import utc_now

    settings = get_settings()
    if settings.log_retention_days <= 0 or SessionLocal is None:
        return

    session = SessionLocal()
    try:
        cutoff = utc_now() - timedelta(days=settings.log_retention_days)
        deleted = build_services(session)["log_repo"].delete_older_than(cutoff)
        if deleted:
            get_logger(__name__).info(
                "Startup pruned %s log events older than %s days",
                deleted,
                settings.log_retention_days,
            )
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, json_format=settings.json_logging)
    Path("data").mkdir(parents=True, exist_ok=True)
    init_db(settings.database_url)
    _prune_expired_logs()
    get_logger(__name__).info(
        "Application started: %s (env=%s, profile=%s, hardening=%s, auth=%s)",
        settings.app_name,
        settings.app_env,
        settings.resolved_security_profile,
        settings.hardening_enabled,
        settings.auth_required,
    )
    yield
    await close_http_client()


def create_app() -> FastAPI:
    settings = get_settings()
    hardening = settings.hardening_enabled

    app = FastAPI(
        title="Observability Watchdog",
        description="Intelligent log anomaly detection with webhook alerting",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if hardening else "/docs",
        redoc_url=None if hardening else "/redoc",
        openapi_url=None if hardening else "/openapi.json",
    )

    if hardening:
        app.add_middleware(ApiKeyAuthMiddleware)
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RequestBodySizeLimitMiddleware)
        app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled error for %s %s",
                request.method,
                request.url.path,
            )
            raise
        finally:
            request_id_var.reset(token)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        if response is not None:
            logger.info(
                "HTTP %s %s -> %s (%.2fms)",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            response.headers["X-Request-ID"] = request_id
            record_http_request(
                request.method,
                request.url.path,
                response.status_code,
                duration_ms / 1000.0,
            )
        return response

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> PlainTextResponse:
        return PlainTextResponse(render_prometheus(), media_type="text/plain; version=0.0.4")

    @app.exception_handler(ConfigurationError)
    async def configuration_error_handler(_: Request, exc: ConfigurationError):
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(AnalysisInProgressError)
    async def analysis_in_progress_handler(_: Request, exc: AnalysisInProgressError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(IngestionParseError)
    async def ingestion_parse_error_handler(_: Request, exc: IngestionParseError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(IngestionError)
    async def ingestion_error_handler(_: Request, exc: IngestionError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(WatchdogError)
    async def watchdog_error_handler(_: Request, exc: WatchdogError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(WebhookDeliveryError)
    async def webhook_error_handler(_: Request, exc: WebhookDeliveryError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            raise exc
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(create_api_router(include_demo=not hardening))

    dashboard_dist = Path("dashboard/dist")
    if settings.serve_dashboard and dashboard_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(dashboard_dist), html=True), name="dashboard")

    return app


app = create_app()
