#!/usr/bin/env python3
"""Run end-to-end demo: ingest, analyze, print summary."""

from __future__ import annotations

import httpx

API = "http://127.0.0.1:8000"


def main() -> None:
    client = httpx.Client(timeout=30.0)

    summary_before = client.get(f"{API}/api/v1/health/summary").json()
    print("Health before analysis:", summary_before)

    analyze = client.post(f"{API}/api/v1/analyze/run").json()
    print("Analysis result:", analyze)

    summary_after = client.get(f"{API}/api/v1/health/summary").json()
    print("Health after analysis:", summary_after)

    deliveries = client.get(f"{API}/api/v1/webhooks/deliveries").json()
    print("Webhook deliveries:", len(deliveries))


if __name__ == "__main__":
    main()
