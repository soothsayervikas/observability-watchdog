from fastapi import APIRouter

from app.api.v1 import alerts, analysis, demo, logs, metrics, sources, webhooks


def create_api_router(*, include_demo: bool = True) -> APIRouter:
    api_router = APIRouter(prefix="/api/v1")
    api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
    api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
    api_router.include_router(analysis.router, prefix="/analyze", tags=["analysis"])
    api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
    api_router.include_router(metrics.router, tags=["metrics"])
    api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    if include_demo:
        api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
    return api_router


# Backward-compatible default router for imports
api_router = create_api_router(include_demo=True)
