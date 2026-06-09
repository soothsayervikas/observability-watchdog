from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest

from app.core.analysis_lock import _redis_acquire, _redis_release, analysis_guard
from app.core.rate_limit import RedisRateLimiter, reset_rate_limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter_state() -> None:
    reset_rate_limiter()
    yield
    reset_rate_limiter()


def test_redis_rate_limiter_blocks_excess_requests() -> None:
    mock_client = MagicMock()
    mock_client.incr.side_effect = [1, 2, 3]
    with patch("redis.Redis.from_url", return_value=mock_client):
        limiter = RedisRateLimiter("redis://localhost:6379/0")
        key = "ci-test-client"
        assert limiter.allow(key, limit=2, window_seconds=60)
        assert limiter.allow(key, limit=2, window_seconds=60)
        assert not limiter.allow(key, limit=2, window_seconds=60)


@pytest.mark.asyncio
async def test_redis_analysis_lock_acquire_and_release() -> None:
    token = "test-token"
    mock_client = MagicMock()
    mock_client.set.side_effect = [True, False]
    mock_client.eval.return_value = 1

    with patch("redis.Redis.from_url", return_value=mock_client):
        assert _redis_acquire("redis://localhost:6379/0", token) is True
        assert _redis_acquire("redis://localhost:6379/0", "other-token") is False
        _redis_release("redis://localhost:6379/0", token)
        mock_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_analysis_guard_uses_redis_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    from app.config import get_settings

    get_settings.cache_clear()

    @asynccontextmanager
    async def fake_redis_guard(_redis_url: str):
        yield

    with patch("app.core.analysis_lock._redis_analysis_guard", fake_redis_guard):
        async with analysis_guard():
            pass

    get_settings.cache_clear()
