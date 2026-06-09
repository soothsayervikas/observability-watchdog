"""Lightweight Prometheus-style metrics (no external dependency)."""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field

_UUID_SEGMENT = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_lock = threading.Lock()


@dataclass
class _Counter:
    name: str
    help: str
    labels: tuple[str, ...]
    values: dict[tuple[str, ...], float] = field(default_factory=dict)

    def inc(self, amount: float = 1.0, **label_values: str) -> None:
        key = tuple(label_values.get(label, "") for label in self.labels)
        with _lock:
            self.values[key] = self.values.get(key, 0.0) + amount


@dataclass
class _Gauge:
    name: str
    help: str
    labels: tuple[str, ...]
    values: dict[tuple[str, ...], float] = field(default_factory=dict)

    def set(self, value: float, **label_values: str) -> None:
        key = tuple(label_values.get(label, "") for label in self.labels)
        with _lock:
            self.values[key] = value


@dataclass
class _Histogram:
    name: str
    help: str
    labels: tuple[str, ...]
    buckets: tuple[float, ...]
    counts: dict[tuple[str, ...], list[int]] = field(default_factory=dict)
    sums: dict[tuple[str, ...], float] = field(default_factory=dict)

    def observe(self, value: float, **label_values: str) -> None:
        key = tuple(label_values.get(label, "") for label in self.labels)
        with _lock:
            if key not in self.counts:
                self.counts[key] = [0] * len(self.buckets)
                self.sums[key] = 0.0
            self.sums[key] += value
            for index, upper in enumerate(self.buckets):
                if value <= upper:
                    self.counts[key][index] += 1


HTTP_REQUESTS = _Counter(
    "watchdog_http_requests_total",
    "Total HTTP requests",
    ("method", "path", "status"),
)

HTTP_DURATION = _Histogram(
    "watchdog_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ("method", "path"),
    (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

INGEST_EVENTS = _Counter("watchdog_ingest_events_total", "Log events ingested", ("result",))

ANALYSIS_RUNS = _Counter("watchdog_analysis_runs_total", "Analysis runs", ("method",))

ALERTS_CREATED = _Counter("watchdog_alerts_created_total", "Alerts created", ("severity",))

WEBHOOK_DELIVERIES = _Counter(
    "watchdog_webhook_deliveries_total",
    "Webhook delivery attempts",
    ("success",),
)

AI_ANALYSIS = _Counter(
    "watchdog_ai_analysis_total",
    "AI analysis outcomes",
    ("status",),
)

DB_UP = _Gauge("watchdog_db_up", "Database connectivity (1=up, 0=down)", ())


def normalize_metric_path(path: str) -> str:
    """Collapse dynamic path segments (e.g. UUIDs) to limit metric cardinality."""
    stripped = path.rstrip("/") or "/"
    if stripped == "/":
        return "/"
    parts = []
    for segment in stripped.split("/"):
        if _UUID_SEGMENT.match(segment):
            parts.append(":id")
        else:
            parts.append(segment)
    return "/".join(parts)


def record_http_request(method: str, path: str, status: int, duration_seconds: float) -> None:
    normalized = normalize_metric_path(path)
    HTTP_REQUESTS.inc(method=method, path=normalized, status=str(status))
    HTTP_DURATION.observe(duration_seconds, method=method, path=normalized)


def _format_labels(label_names: tuple[str, ...], label_values: tuple[str, ...]) -> str:
    if not label_names:
        return ""
    pairs = [f'{name}="{value}"' for name, value in zip(label_names, label_values, strict=True)]
    return "{" + ",".join(pairs) + "}"


def render_prometheus() -> str:
    lines: list[str] = []

    lines.append(f"# HELP {HTTP_REQUESTS.name} {HTTP_REQUESTS.help}")
    lines.append(f"# TYPE {HTTP_REQUESTS.name} counter")
    with _lock:
        for key, value in HTTP_REQUESTS.values.items():
            labels = _format_labels(HTTP_REQUESTS.labels, key)
            lines.append(f"{HTTP_REQUESTS.name}{labels} {value}")

        lines.append(f"# HELP {HTTP_DURATION.name} {HTTP_DURATION.help}")
        lines.append(f"# TYPE {HTTP_DURATION.name} histogram")
        for key, bucket_counts in HTTP_DURATION.counts.items():
            labels = _format_labels(HTTP_DURATION.labels, key)
            cumulative = 0
            for upper, count in zip(HTTP_DURATION.buckets, bucket_counts, strict=True):
                cumulative += count
                lines.append(f'{HTTP_DURATION.name}_bucket{labels},le="{upper}" {cumulative}')
            lines.append(f'{HTTP_DURATION.name}_bucket{labels},le="+Inf" {cumulative}')
            lines.append(f"{HTTP_DURATION.name}_sum{labels} {HTTP_DURATION.sums.get(key, 0.0)}")
            lines.append(f"{HTTP_DURATION.name}_count{labels} {sum(bucket_counts)}")

        for metric in (
            INGEST_EVENTS,
            ANALYSIS_RUNS,
            ALERTS_CREATED,
            WEBHOOK_DELIVERIES,
            AI_ANALYSIS,
        ):
            lines.append(f"# HELP {metric.name} {metric.help}")
            lines.append(f"# TYPE {metric.name} counter")
            for key, value in metric.values.items():
                labels = _format_labels(metric.labels, key)
                lines.append(f"{metric.name}{labels} {value}")

        lines.append(f"# HELP {DB_UP.name} {DB_UP.help}")
        lines.append(f"# TYPE {DB_UP.name} gauge")
        for key, value in DB_UP.values.items():
            labels = _format_labels(DB_UP.labels, key)
            lines.append(f"{DB_UP.name}{labels} {value}")

    lines.append(f"watchdog_metrics_rendered_at {time.time():.3f}")
    return "\n".join(lines) + "\n"
