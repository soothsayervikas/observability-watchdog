from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api import deps
from app.api.deps import build_services
from app.config import get_settings
from app.core.analysis_lock import analysis_guard
from app.core.exceptions import ConfigurationError, WebhookDeliveryError
from app.core.logging import get_logger
from app.core.metrics import ALERTS_CREATED, ANALYSIS_RUNS
from app.models.domain import AnalyzeResponse
from app.services.analysis_service import enrich_phase_with_ai

router = APIRouter()
logger = get_logger(__name__)


async def _dispatch_webhooks(alert_ids: list[str]) -> int:
    """Deliver webhooks synchronously; return count of failures."""
    if deps.SessionLocal is None:
        return len(alert_ids)

    failures = 0
    session = deps.SessionLocal()
    try:
        services = build_services(session)
        for alert_id in alert_ids:
            alert = services["alert_repo"].get_by_id(alert_id)
            if not alert:
                continue
            try:
                await services["webhook"].dispatch_alert(alert)
            except WebhookDeliveryError as exc:
                failures += 1
                logger.error("Webhook delivery failed for alert %s: %s", alert_id, exc)
    finally:
        session.close()
    return failures


def _response_status(webhook_status: str) -> int:
    if webhook_status == "failed":
        return 502
    if webhook_status == "partial_failure":
        return 207
    return 200


@router.post(
    "/run",
    response_model=AnalyzeResponse,
    responses={
        200: {"description": "Analysis completed; webhooks delivered or not required"},
        207: {"description": "Analysis completed; some webhook deliveries failed"},
        502: {"description": "Analysis completed; all webhook deliveries failed"},
    },
)
async def run_analysis(
    lookback_hours: int | None = Query(default=None, ge=1, le=168),
) -> AnalyzeResponse | JSONResponse:
    settings = get_settings()

    async with analysis_guard():
        if deps.SessionLocal is None:
            raise ConfigurationError("Database not initialized")

        session = deps.SessionLocal()
        try:
            phase = await run_in_threadpool(
                build_services(session)["analysis"].run_statistical_phase,
                lookback_hours=lookback_hours,
            )
        finally:
            session.close()

        enrichment = await enrich_phase_with_ai(settings, phase)

        session = deps.SessionLocal()
        try:
            services = build_services(session)
            created_alerts = await run_in_threadpool(
                services["analysis"].persist_analysis_results,
                phase,
                enrichment,
            )
            alert_responses = [services["alerts"].to_response(alert) for alert in created_alerts]
        finally:
            session.close()

    webhook_status = "none"
    webhook_failures = 0
    if created_alerts:
        webhook_failures = await _dispatch_webhooks([alert.id for alert in created_alerts])
        total = len(created_alerts)
        if webhook_failures == 0:
            webhook_status = "completed"
        elif webhook_failures >= total:
            webhook_status = "failed"
        else:
            webhook_status = "partial_failure"

    ANALYSIS_RUNS.inc(method=enrichment.detection_method)
    for alert in created_alerts:
        ALERTS_CREATED.inc(severity=alert.severity)

    body = AnalyzeResponse(
        alerts_created=len(created_alerts),
        alerts=alert_responses,
        buckets_analyzed=phase.buckets_analyzed,
        ai_enabled=settings.ai_classifier_enabled and bool(settings.azure_openai_api_key),
        ai_assessment=enrichment.ai_assessment,
        ai_status=enrichment.ai_status,
        ai_error=enrichment.ai_error,
        detection_method=enrichment.detection_method,
        webhook_status=webhook_status,
        webhook_failures=webhook_failures,
    )

    status_code = _response_status(webhook_status)
    if status_code == 200:
        return body
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))
