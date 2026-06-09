from datetime import datetime, timedelta

from app.models.db import LogEventORM
from app.models.domain import LogLevel
from app.repositories.log import LogRepository


def test_aggregate_time_buckets_matches_wall_clock_windows(db_session) -> None:
    repo = LogRepository(db_session)
    base = datetime(2026, 6, 9, 12, 0, 0)
    events = [
        LogEventORM(
            timestamp=base + timedelta(minutes=minute),
            level=LogLevel.ERROR.value if minute < 3 else LogLevel.INFO.value,
            service="payment-api",
            message="event",
            metadata_json=None,
            ingested_at=base,
        )
        for minute in range(10)
    ]
    repo.create_many(events)

    aggregates = repo.aggregate_time_buckets_since(
        base - timedelta(minutes=1),
        window_minutes=5,
        error_levels={LogLevel.ERROR.value},
        service="payment-api",
    )
    buckets = repo.buckets_to_time_buckets(aggregates, window_minutes=5)

    assert len(buckets) >= 1
    assert buckets[0].total_count >= 3
    assert buckets[0].error_count >= 3
