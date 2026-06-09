"""Prevent concurrent analysis runs from racing on alert creation."""

from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager

from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.core.exceptions import AnalysisInProgressError

_analysis_lock = asyncio.Lock()
_analysis_active = False

_REDIS_LOCK_KEY = "watchdog:analysis_lock"
_REDIS_LOCK_TTL_SECONDS = 300
_REDIS_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
else
    return 0
end
"""


def is_analysis_running() -> bool:
    return _analysis_active


def get_analysis_lock() -> asyncio.Lock:
    return _analysis_lock


def reset_analysis_state() -> None:
    """Reset active flag — used in tests."""
    global _analysis_active
    _analysis_active = False


def _redis_acquire(redis_url: str, token: str) -> bool:
    import redis

    client = redis.Redis.from_url(redis_url)
    try:
        return bool(client.set(_REDIS_LOCK_KEY, token, nx=True, ex=_REDIS_LOCK_TTL_SECONDS))
    finally:
        client.close()


def _redis_release(redis_url: str, token: str) -> None:
    import redis

    client = redis.Redis.from_url(redis_url)
    try:
        client.eval(_REDIS_RELEASE_SCRIPT, 1, _REDIS_LOCK_KEY, token)
    finally:
        client.close()


@asynccontextmanager
async def _local_analysis_guard():
    global _analysis_active
    async with _analysis_lock:
        if _analysis_active:
            raise AnalysisInProgressError("Analysis already in progress")
        _analysis_active = True
    try:
        yield
    finally:
        async with _analysis_lock:
            _analysis_active = False


@asynccontextmanager
async def _redis_analysis_guard(redis_url: str):
    token = str(uuid.uuid4())
    acquired = await run_in_threadpool(_redis_acquire, redis_url, token)
    if not acquired:
        raise AnalysisInProgressError("Analysis already in progress")
    try:
        yield
    finally:
        await run_in_threadpool(_redis_release, redis_url, token)


@asynccontextmanager
async def analysis_guard():
    """Reject concurrent analysis; use Redis when configured for multi-worker safety."""
    settings = get_settings()
    if settings.redis_url:
        try:
            async with _redis_analysis_guard(settings.redis_url):
                yield
            return
        except ImportError:
            pass

    async with _local_analysis_guard():
        yield
