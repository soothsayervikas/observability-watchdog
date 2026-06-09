#!/usr/bin/env python3
"""Production-style log collector agent.

Watches a directory for new log files and either:
  1) POSTs them to the API upload endpoint, or
  2) Triggers the server-side /api/v1/sources/scan endpoint.

Usage:
  python scripts/log_collector.py --mode scan
  python scripts/log_collector.py --mode watch --interval 10
"""

from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

import httpx

DEFAULT_API = "http://127.0.0.1:8000"
SUPPORTED = {".json", ".jsonl", ".ndjson", ".log", ".txt"}


def scan_via_api(api_base: str) -> dict:
    response = httpx.post(f"{api_base}/api/v1/sources/scan", timeout=60.0)
    response.raise_for_status()
    return response.json()


def upload_file(api_base: str, file_path: Path, default_service: str) -> dict:
    with file_path.open("rb") as handle:
        response = httpx.post(
            f"{api_base}/api/v1/logs/upload",
            files={"file": (file_path.name, handle)},
            data={"default_service": default_service},
            timeout=60.0,
        )
    response.raise_for_status()
    return response.json()


def watch_and_upload(
    api_base: str,
    watch_dir: Path,
    processed_dir: Path,
    *,
    interval: int,
    default_service: str,
) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    print(f"Watching {watch_dir} every {interval}s ...")

    while True:
        for file_path in sorted(watch_dir.iterdir()):
            if not file_path.is_file() or file_path.suffix.lower() not in SUPPORTED:
                continue
            try:
                result = upload_file(api_base, file_path, default_service)
                shutil.move(str(file_path), processed_dir / file_path.name)
                print(
                    f"Ingested {file_path.name}: accepted={result['accepted']} "
                    f"format={result['format_detected']}"
                )
            except Exception as exc:  # noqa: BLE001
                print(f"Failed to ingest {file_path.name}: {exc}")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Observability watchdog log collector")
    parser.add_argument("--api", default=DEFAULT_API)
    parser.add_argument("--mode", choices=["scan", "watch", "upload"], default="scan")
    parser.add_argument("--watch-dir", default="data/incoming")
    parser.add_argument("--processed-dir", default="data/incoming/processed")
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--default-service", default="app-service")
    parser.add_argument("--file")
    args = parser.parse_args()

    if args.mode == "scan":
        result = scan_via_api(args.api)
        print(result)
        return

    if args.mode == "upload":
        if not args.file:
            raise SystemExit("--file is required for upload mode")
        result = upload_file(args.api, Path(args.file), args.default_service)
        print(result)
        return

    watch_and_upload(
        args.api,
        Path(args.watch_dir),
        Path(args.processed_dir),
        interval=args.interval,
        default_service=args.default_service,
    )


if __name__ == "__main__":
    main()
