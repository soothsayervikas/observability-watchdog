#!/usr/bin/env python3
"""Smoke test the docker-compose stack in CI (API + webhook)."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta

import httpx

API = "http://127.0.0.1:8000"
READY_TIMEOUT_SECONDS = 120


def wait_for_ready() -> None:
    deadline = time.time() + READY_TIMEOUT_SECONDS
    while time.time() < deadline:
        try:
            response = httpx.get(f"{API}/api/v1/health/ready", timeout=5)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    raise RuntimeError(f"API not ready after {READY_TIMEOUT_SECONDS}s")


def main() -> int:
    wait_for_ready()

    health = httpx.get(f"{API}/api/v1/health", timeout=10)
    health.raise_for_status()

    base = datetime.utcnow()
    events = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "ERROR" if minute < 8 else "INFO",
            "service": "ci-smoke",
            "message": "synthetic failure" if minute < 8 else "ok",
        }
        for minute in range(20, -1, -1)
        for _ in range(8)
    ]
    ingest = httpx.post(f"{API}/api/v1/logs/ingest", json={"events": events}, timeout=30)
    ingest.raise_for_status()
    assert ingest.json()["accepted"] >= 1

    analyze = httpx.post(f"{API}/api/v1/analyze/run", timeout=60)
    analyze.raise_for_status()

    summary = httpx.get(f"{API}/api/v1/health/summary", timeout=10)
    summary.raise_for_status()

    print("Docker smoke test passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Docker smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
