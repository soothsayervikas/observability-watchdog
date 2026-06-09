from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.config import Settings
from app.core.ai_cache import (
    _MAX_CACHE_ENTRIES,
    clear_ai_cache,
    get_cached,
    payload_hash,
    set_cached,
)
from app.core.analysis_lock import analysis_guard, reset_analysis_state
from app.core.exceptions import AnalysisInProgressError
from app.models.db import LogEventORM
from app.models.domain import LogLevel
from app.repositories.alert import AlertRepository
from app.repositories.log import LogRepository
from app.repositories.metrics import MetricsRepository
from app.services.metrics_service import MetricsService


def test_ai_cache_evicts_oldest_when_full() -> None:
    clear_ai_cache()
    for index in range(_MAX_CACHE_ENTRIES + 1):
        set_cached(f"key-{index}", {"index": index})
    assert get_cached("key-0", ttl_seconds=60) is None
    assert get_cached(f"key-{_MAX_CACHE_ENTRIES}", ttl_seconds=60) == {"index": _MAX_CACHE_ENTRIES}
    clear_ai_cache()


def test_ai_cache_hit_and_miss() -> None:
    clear_ai_cache()
    key = payload_hash({"sample": "data"})
    assert get_cached(key, ttl_seconds=60) is None
    set_cached(key, {"ok": True})
    assert get_cached(key, ttl_seconds=60) == {"ok": True}
    clear_ai_cache()
    assert get_cached(key, ttl_seconds=60) is None


def test_health_summary_scoped_to_lookback(db_session) -> None:
    repo = LogRepository(db_session)
    now = datetime(2026, 6, 9, 12, 0, 0)
    old = LogEventORM(
        timestamp=now - timedelta(hours=48),
        level=LogLevel.ERROR.value,
        service="api",
        message="old error",
        metadata_json=None,
        ingested_at=now,
    )
    recent = LogEventORM(
        timestamp=now - timedelta(hours=1),
        level=LogLevel.INFO.value,
        service="api",
        message="recent info",
        metadata_json=None,
        ingested_at=now,
    )
    repo.create_many([old, recent])

    settings = Settings(analysis_lookback_hours=24)
    service = MetricsService(
        repo,
        AlertRepository(db_session),
        MetricsRepository(db_session),
        settings,
    )

    with patch("app.services.metrics_service.utc_now", return_value=now):
        summary = service.health_summary()

    assert summary["total_logs"] == 1
    assert summary["error_count"] == 0


@pytest.mark.asyncio
async def test_analysis_guard_rejects_concurrent_runs() -> None:
    reset_analysis_state()
    async with analysis_guard():
        with pytest.raises(AnalysisInProgressError):
            async with analysis_guard():
                pass
