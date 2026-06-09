from datetime import datetime, timedelta
from types import SimpleNamespace

from app.services.detection.statistical import (
    TimeBucket,
    bucketize_logs,
    compute_health_score,
    detect_error_spikes,
    wall_clock_bucket_start,
)


def _log(timestamp: datetime, level: str) -> SimpleNamespace:
    return SimpleNamespace(timestamp=timestamp, level=level)


def test_bucketize_logs_groups_by_window() -> None:
    start = datetime(2026, 6, 8, 10, 0, 0)
    logs = [
        _log(start + timedelta(minutes=1), "INFO"),
        _log(start + timedelta(minutes=2), "ERROR"),
        _log(start + timedelta(minutes=6), "INFO"),
    ]
    buckets = bucketize_logs(logs, window_minutes=5)
    assert len(buckets) == 2
    assert buckets[0].error_count == 1
    assert buckets[1].error_count == 0


def test_detect_error_spike_on_high_error_rate() -> None:
    start = datetime(2026, 6, 8, 10, 0, 0)
    stable = [
        TimeBucket(
            start + timedelta(minutes=idx * 5), start + timedelta(minutes=(idx + 1) * 5), 100, 2
        )
        for idx in range(6)
    ]
    spike = TimeBucket(start + timedelta(minutes=30), start + timedelta(minutes=35), 100, 40)
    results = detect_error_spikes(
        stable + [spike],
        baseline_buckets=6,
        z_threshold=2.0,
        min_error_count=5,
    )
    assert len(results) == 1
    assert results[0].severity.value in {"HIGH", "CRITICAL", "MEDIUM"}


def test_no_spike_on_stable_traffic() -> None:
    start = datetime(2026, 6, 8, 10, 0, 0)
    buckets = [
        TimeBucket(
            start + timedelta(minutes=idx * 5), start + timedelta(minutes=(idx + 1) * 5), 100, 2
        )
        for idx in range(8)
    ]
    results = detect_error_spikes(
        buckets,
        baseline_buckets=6,
        z_threshold=2.5,
        min_error_count=5,
    )
    assert results == []


def test_detect_single_bucket_spike_when_error_rate_high() -> None:
    start = datetime(2026, 6, 8, 10, 0, 0)
    bucket = TimeBucket(start, start + timedelta(minutes=5), 40, 12)
    results = detect_error_spikes(
        [bucket],
        baseline_buckets=6,
        z_threshold=2.5,
        min_error_count=5,
    )
    assert len(results) == 1


def test_wall_clock_bucket_alignment() -> None:
    ts = datetime(2026, 6, 8, 10, 7, 30)
    bucket = wall_clock_bucket_start(ts, window_minutes=5)
    assert bucket == datetime(2026, 6, 8, 10, 5, 0)


def test_health_score_penalizes_errors_and_alerts() -> None:
    score = compute_health_score(
        error_rate=0.2,
        open_critical_alerts=2,
        open_high_alerts=1,
        recent_spike_count=2,
    )
    assert score < 50
