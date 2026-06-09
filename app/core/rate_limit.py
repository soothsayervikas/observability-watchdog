from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Protocol

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RateLimiterBackend(Protocol):
    def allow(self, key: str, *, limit: int, window_seconds: int = 60) -> bool: ...


@dataclass
class _ClientWindow:
    timestamps: deque[float] = field(default_factory=deque)


class InMemoryRateLimiter:
    """Sliding-window rate limiter keyed by client IP (single-process only)."""

    def __init__(self) -> None:
        self._windows: dict[str, _ClientWindow] = defaultdict(_ClientWindow)

    def allow(self, key: str, *, limit: int, window_seconds: int = 60) -> bool:
        if limit <= 0:
            return True

        now = time.monotonic()
        window = self._windows[key]
        cutoff = now - window_seconds

        while window.timestamps and window.timestamps[0] <= cutoff:
            window.timestamps.popleft()

        if len(window.timestamps) >= limit:
            return False

        window.timestamps.append(now)
        return True


class RedisRateLimiter:
    """Distributed fixed-window limiter backed by Redis."""

    def __init__(self, redis_url: str) -> None:
        import redis

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def allow(self, key: str, *, limit: int, window_seconds: int = 60) -> bool:
        if limit <= 0:
            return True

        now = int(time.time())
        bucket = f"ratelimit:{key}:{now // window_seconds}"
        count = int(self._client.incr(bucket))
        if count == 1:
            self._client.expire(bucket, window_seconds + 1)
        return count <= limit


_rate_limiter: RateLimiterBackend | None = None


def get_rate_limiter(settings: Settings | None = None) -> RateLimiterBackend:
    global _rate_limiter
    if _rate_limiter is not None:
        return _rate_limiter

    settings = settings or get_settings()
    if settings.redis_url:
        try:
            _rate_limiter = RedisRateLimiter(settings.redis_url)
            logger.info("Rate limiter using Redis backend")
            return _rate_limiter
        except Exception as exc:
            logger.warning(
                "Redis rate limiter unavailable (%s); falling back to in-memory limiter",
                exc,
            )

    _rate_limiter = InMemoryRateLimiter()
    return _rate_limiter


def reset_rate_limiter() -> None:
    """Reset cached limiter — used in tests."""
    global _rate_limiter
    _rate_limiter = None


def _client_key(request: Request) -> str:
    settings = get_settings()
    if settings.trusted_proxy:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _limit_for_path(settings: Settings, path: str) -> int:
    if path.startswith("/api/v1/logs"):
        return settings.rate_limit_ingest_per_minute
    if path.startswith("/api/v1/analyze"):
        return settings.rate_limit_analyze_per_minute
    if path.startswith("/api/v1/"):
        return settings.rate_limit_default_per_minute
    return settings.rate_limit_default_per_minute


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # noqa: ANN201
        settings = get_settings()
        if (
            not settings.hardening_enabled
            or not settings.rate_limit_enabled
            or request.method == "OPTIONS"
        ):
            return await call_next(request)

        limit = _limit_for_path(settings, request.url.path)
        key = f"{_client_key(request)}:{request.url.path}"
        limiter = get_rate_limiter(settings)
        if not limiter.allow(key, limit=limit, window_seconds=60):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)
