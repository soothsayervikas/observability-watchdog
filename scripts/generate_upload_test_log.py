#!/usr/bin/env python3
"""Generate a plain-text log file for dashboard upload testing."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "test-upload-spike.log"


def main() -> None:
    base = datetime.now(UTC).replace(microsecond=0)
    lines = [
        "# Observability Watchdog — upload test log",
        "# Upload via dashboard: Upload Log File",
        "# Then click Run Analysis to detect the error spike",
        "",
    ]

    for minute in range(60, 14, -5):
        ts = (base - timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for i in range(8):
            svc = "payment-api" if i % 2 == 0 else "auth-service"
            lines.append(f"{ts} INFO [{svc}] - Request completed successfully id={minute}-{i}")

    for minute in range(14, -1, -1):
        ts = (base - timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for _ in range(12):
            lines.append(f"{ts} ERROR [payment-api] - Database connection timeout pool exhausted")
        for i in range(3):
            lines.append(f"{ts} INFO [payment-api] - Retrying database connection attempt={i}")

    for minute in range(5, -1, -1):
        ts = (base - timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for _ in range(4):
            lines.append(f"{ts} ERROR [auth-service] - JWT validation failed invalid signature")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} lines to {OUTPUT}")
    print(f"Spike window ends at {base.isoformat().replace('+00:00', 'Z')}")


if __name__ == "__main__":
    main()
