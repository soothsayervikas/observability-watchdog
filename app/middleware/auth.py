from __future__ import annotations

import secrets

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import get_settings

# Probes and metrics stay public so load balancers / Prometheus can scrape without credentials.
_PUBLIC_PATHS = frozenset({"/api/v1/health", "/api/v1/health/ready", "/metrics"})


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if not settings.auth_required:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path.rstrip("/") or "/"
        if path in _PUBLIC_PATHS:
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if not provided or not secrets.compare_digest(provided, settings.api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        return await call_next(request)
