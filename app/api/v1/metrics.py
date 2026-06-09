from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import build_services, get_db_session
from app.config import get_settings
from app.core.metrics import DB_UP
from app.models.domain import HealthSummaryResponse, TrendPoint, TrendsResponse

router = APIRouter()


@router.get("/health")
def liveness() -> dict[str, str | bool]:
    settings = get_settings()
    if settings.hardening_enabled:
        return {"status": "ok"}
    return {
        "status": "ok",
        "environment": settings.app_env,
        "security_profile": settings.resolved_security_profile,
        "hardening_enabled": settings.hardening_enabled,
        "auth_required": settings.auth_required,
    }


@router.get("/health/ready", response_model=None)
def readiness(session: Session = Depends(get_db_session)) -> JSONResponse:
    try:
        session.execute(text("SELECT 1"))
        DB_UP.set(1)
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "database": True},
        )
    except Exception:
        DB_UP.set(0)
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": False},
        )


@router.get("/health/summary", response_model=HealthSummaryResponse)
def health_summary(session: Session = Depends(get_db_session)) -> HealthSummaryResponse:
    services = build_services(session)
    summary = services["metrics"].health_summary()
    return HealthSummaryResponse(**summary)


@router.get("/metrics/trends", response_model=TrendsResponse)
def metrics_trends(
    service: str | None = None,
    hours: int = Query(default=24, ge=1, le=168),
    session: Session = Depends(get_db_session),
) -> TrendsResponse:
    services = build_services(session)
    points = services["metrics"].trends(service=service, hours=hours)
    return TrendsResponse(
        points=[
            TrendPoint(
                bucket_start=point.bucket_start,
                bucket_end=point.bucket_end,
                service=point.service,
                total_count=point.total_count,
                error_count=point.error_count,
                error_rate=point.error_rate,
            )
            for point in points
        ]
    )
