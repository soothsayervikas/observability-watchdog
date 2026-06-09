from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean, pstdev
from typing import Any

from app.models.domain import AlertSeverity, AlertType, LogLevel

DEFAULT_ERROR_LEVELS = {LogLevel.ERROR.value, LogLevel.FATAL.value}


@dataclass(frozen=True)
class TimeBucket:
    start: datetime
    end: datetime
    total_count: int
    error_count: int

    @property
    def error_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.error_count / self.total_count


@dataclass(frozen=True)
class SpikeDetectionResult:
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    window_start: datetime
    window_end: datetime
    metrics: dict[str, Any]
    dedupe_key: str


@dataclass(frozen=True)
class DetectionThresholds:
    min_error_rate: float = 0.2
    zero_baseline_rate: float = 0.2
    severity_critical_rate: float = 0.5
    severity_high_rate: float = 0.25
    severity_medium_rate: float = 0.1


def wall_clock_bucket_start(timestamp: datetime, *, window_minutes: int) -> datetime:
    """Align buckets to fixed wall-clock windows (e.g. :00, :05, :10)."""
    minute = (timestamp.minute // window_minutes) * window_minutes
    return timestamp.replace(minute=minute, second=0, microsecond=0)


def bucketize_logs(
    logs: list[Any],
    *,
    window_minutes: int,
    error_levels: set[str] | None = None,
) -> list[TimeBucket]:
    if not logs:
        return []

    levels = error_levels or DEFAULT_ERROR_LEVELS
    window = timedelta(minutes=window_minutes)
    counts: dict[datetime, list[int]] = defaultdict(lambda: [0, 0])

    for log in logs:
        bucket_start = wall_clock_bucket_start(log.timestamp, window_minutes=window_minutes)
        counts[bucket_start][0] += 1
        if log.level in levels:
            counts[bucket_start][1] += 1

    return [
        TimeBucket(
            start=bucket_start,
            end=bucket_start + window,
            total_count=counts[bucket_start][0],
            error_count=counts[bucket_start][1],
        )
        for bucket_start in sorted(counts)
        if counts[bucket_start][0] > 0
    ]


def _build_spike_result(
    current: TimeBucket,
    *,
    baseline_mean: float,
    delta_percent: float,
    service: str | None,
    thresholds: DetectionThresholds,
) -> SpikeDetectionResult:
    severity = _severity_from_spike(
        current.error_rate,
        delta_percent,
        current.error_count,
        thresholds=thresholds,
    )
    service_key = service or "global"
    dedupe_key = f"ERROR_SPIKE:{service_key}:{current.start.isoformat()}:{current.end.isoformat()}"
    service_label = f" for service '{service}'" if service else ""
    title = f"Error rate spike detected{service_label}"
    return SpikeDetectionResult(
        alert_type=AlertType.ERROR_SPIKE,
        severity=severity,
        title=title,
        description=(
            f"Error rate increased to {current.error_rate:.1%} "
            f"(baseline {baseline_mean:.1%}, delta {delta_percent:.0f}%)."
        ),
        window_start=current.start,
        window_end=current.end,
        metrics={
            "service": service,
            "baseline_error_rate": round(baseline_mean, 4),
            "current_error_rate": round(current.error_rate, 4),
            "delta_percent": round(delta_percent, 2),
            "error_count": current.error_count,
            "total_count": current.total_count,
        },
        dedupe_key=dedupe_key,
    )


def detect_error_spikes(
    buckets: list[TimeBucket],
    *,
    baseline_buckets: int,
    z_threshold: float,
    min_error_count: int,
    service: str | None = None,
    thresholds: DetectionThresholds | None = None,
) -> list[SpikeDetectionResult]:
    if not buckets:
        return []

    cfg = thresholds or DetectionThresholds()

    if len(buckets) == 1:
        current = buckets[0]
        if current.error_count >= min_error_count and current.error_rate >= cfg.min_error_rate:
            return [
                _build_spike_result(
                    current,
                    baseline_mean=0.0,
                    delta_percent=0.0,
                    service=service,
                    thresholds=cfg,
                )
            ]
        return []

    results: list[SpikeDetectionResult] = []
    for index in range(1, len(buckets)):
        current = buckets[index]
        history = buckets[max(0, index - baseline_buckets) : index]
        if not history or current.total_count == 0:
            continue

        baseline_rates = [bucket.error_rate for bucket in history]
        baseline_mean = mean(baseline_rates)
        baseline_std = pstdev(baseline_rates) if len(baseline_rates) > 1 else 0.0
        threshold = baseline_mean + (z_threshold * baseline_std)

        is_spike = current.error_count >= min_error_count and (
            current.error_rate > threshold
            or (baseline_mean == 0 and current.error_rate > cfg.zero_baseline_rate)
        )
        if not is_spike:
            continue

        delta_percent = 0.0
        if baseline_mean > 0:
            delta_percent = ((current.error_rate - baseline_mean) / baseline_mean) * 100

        results.append(
            _build_spike_result(
                current,
                baseline_mean=baseline_mean,
                delta_percent=delta_percent,
                service=service,
                thresholds=cfg,
            )
        )

    return results


def _severity_from_spike(
    error_rate: float,
    delta_percent: float,
    error_count: int,
    *,
    thresholds: DetectionThresholds,
) -> AlertSeverity:
    if (
        error_rate >= thresholds.severity_critical_rate
        or error_count >= 100
        or delta_percent >= 500
    ):
        return AlertSeverity.CRITICAL
    if error_rate >= thresholds.severity_high_rate or error_count >= 50 or delta_percent >= 200:
        return AlertSeverity.HIGH
    if error_rate >= thresholds.severity_medium_rate or error_count >= 20:
        return AlertSeverity.MEDIUM
    return AlertSeverity.LOW


def compute_health_score(
    *,
    error_rate: float,
    open_critical_alerts: int,
    open_high_alerts: int,
    recent_spike_count: int,
) -> int:
    score = 100.0
    score -= min(40.0, error_rate * 400)
    score -= min(30.0, open_critical_alerts * 15)
    score -= min(20.0, open_high_alerts * 8)
    score -= min(10.0, recent_spike_count * 5)
    return max(0, round(score))
