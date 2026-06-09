#!/usr/bin/env python3
"""Seed the API with sample log data."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import httpx

DEFAULT_API = "http://127.0.0.1:8000"


def load_events(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["events"]


def ingest(api_base: str, events: list[dict]) -> None:
    response = httpx.post(
        f"{api_base}/api/v1/logs/ingest",
        json={"events": events},
        timeout=30.0,
    )
    response.raise_for_status()
    print(response.json())


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed observability watchdog with sample logs")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument(
        "--dataset",
        default="error_spike",
        choices=["normal_traffic", "error_spike"],
    )
    args = parser.parse_args()

    sample_path = (
        Path(__file__).resolve().parent.parent / "data" / "samples" / f"{args.dataset}.json"
    )
    if not sample_path.exists():
        raise SystemExit(
            f"Sample file missing: {sample_path}. Run scripts/generate_samples.py first."
        )

    events = load_events(sample_path)
    ingest(args.api, events)
    print(f"Ingested {len(events)} events from {args.dataset}")


if __name__ == "__main__":
    main()
