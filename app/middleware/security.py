from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.config import get_settings

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-XSS-Protection": "0",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject oversized request bodies by counting bytes as they are received."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method not in {"POST", "PUT", "PATCH"}:
            return await call_next(request)

        settings = get_settings()
        if not settings.hardening_enabled:
            return await call_next(request)

        max_bytes = settings.effective_log_max_raw_body_bytes
        received = 0
        too_large = False

        async def limited_receive() -> dict:
            nonlocal received, too_large
            if too_large:
                return {"type": "http.disconnect"}
            message = await request.receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > max_bytes:
                    too_large = True
                    return {"type": "http.disconnect"}
            return message

        wrapped = Request(request.scope, receive=limited_receive)
        response = await call_next(wrapped)
        if too_large:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": (
                        f"Request body exceeds {settings.effective_log_max_raw_body_mb} MB limit"
                    )
                },
            )
        return response
