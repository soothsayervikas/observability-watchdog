#!/usr/bin/env python3
"""Generate sample log datasets for demo and testing."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "data" / "samples"


def _event(minutes_ago: int, level: str, service: str, message: str) -> dict:
    return {
        "timestamp": (datetime.utcnow() - timedelta(minutes=minutes_ago)).isoformat() + "Z",
        "level": level,
        "service": service,
        "message": message,
        "metadata": {"host": "app-01"},
    }


def build_normal_traffic() -> list[dict]:
    events: list[dict] = []
    for minute in range(120, 10, -5):
        for _ in range(8):
            events.append(_event(minute, "INFO", "payment-api", "Processed payment successfully"))
        if minute % 20 == 0:
            events.append(_event(minute, "WARN", "payment-api", "Slow downstream dependency"))
    return events


def build_error_spike() -> list[dict]:
    events = build_normal_traffic()
    for minute in range(9, -1, -1):
        for _ in range(12):
            events.append(_event(minute, "ERROR", "payment-api", "Database connection timeout"))
        events.append(_event(minute, "FATAL", "payment-api", "Circuit breaker opened"))
    return events


def write_dataset(name: str, events: list[dict]) -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    path = BASE / f"{name}.json"
    path.write_text(json.dumps({"events": events}, indent=2), encoding="utf-8")
    print(f"Wrote {path} ({len(events)} events)")


if __name__ == "__main__":
    write_dataset("normal_traffic", build_normal_traffic())
    write_dataset("error_spike", build_error_spike())
