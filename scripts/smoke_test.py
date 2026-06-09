#!/usr/bin/env python3
"""Quick smoke test against running local servers."""

from __future__ import annotations

import sys
import time

import httpx

API = "http://127.0.0.1:8000"
DASHBOARD = "http://127.0.0.1:5173"


def check(name: str, fn) -> bool:
    try:
        response = fn()
        print(f"OK   {name}: HTTP {response.status_code}")
        return response
    except Exception as exc:
        print(f"FAIL {name}: {exc}")
        return None


def main() -> int:
    ok = True

    health = check("API health", lambda: httpx.get(f"{API}/api/v1/health", timeout=10))
    if health is None:
        return 1
    print(f"     {health.json()}")

    seed = check(
        "Demo seed",
        lambda: httpx.post(f"{API}/api/v1/demo/seed?dataset=error_spike", timeout=30),
    )
    if seed is None:
        ok = False
    else:
        body = seed.json()
        print(f"     accepted={body.get('accepted')} rejected={body.get('rejected')}")

    analyze = check("Analyze", lambda: httpx.post(f"{API}/api/v1/analyze/run", timeout=60))
    if analyze is None:
        ok = False
    else:
        body = analyze.json()
        print(
            f"     alerts_created={body.get('alerts_created')} "
            f"method={body.get('detection_method')} "
            f"buckets={body.get('buckets_analyzed')}"
        )
        if body.get("alerts_created", 0) < 1:
            print("WARN analyze returned zero new alerts (may be deduped from prior run)")

    summary = check("Health summary", lambda: httpx.get(f"{API}/api/v1/health/summary", timeout=10))
    if summary:
        body = summary.json()
        print(
            f"     score={body.get('health_score')} logs={body.get('total_logs')} "
            f"open_alerts={body.get('open_alerts')}"
        )

    alerts = check("Alerts list", lambda: httpx.get(f"{API}/api/v1/alerts", timeout=10))
    if alerts:
        print(f"     count={len(alerts.json())}")

    trends = check("Trends", lambda: httpx.get(f"{API}/api/v1/metrics/trends", timeout=10))
    if trends:
        print(f"     points={len(trends.json().get('points', []))}")

    time.sleep(2)
    deliveries = check(
        "Webhook deliveries",
        lambda: httpx.get(f"{API}/api/v1/webhooks/deliveries", timeout=10),
    )
    if deliveries:
        items = deliveries.json()
        successes = sum(1 for item in items if item.get("success"))
        print(f"     count={len(items)} success={successes}")

    dashboard = check("Dashboard", lambda: httpx.get(DASHBOARD, timeout=10))
    if dashboard is None:
        ok = False

    webhook = check(
        "Webhook receiver (POST)",
        lambda: httpx.post(
            "http://127.0.0.1:8765/webhook",
            json={"test": True},
            timeout=10,
        ),
    )
    if webhook is None:
        ok = False

    print("\nSmoke test", "PASSED" if ok else "COMPLETED WITH WARNINGS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
