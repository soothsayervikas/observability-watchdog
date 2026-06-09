#!/usr/bin/env python3
"""Fail CI if likely secrets are present in tracked source files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCAN_DIRS = ("app", "dashboard/src", "scripts", "tests", "docs")
SCAN_FILES = (
    "README.md",
    "prompts.md",
    "pyproject.toml",
    ".env.example",
    ".env.production.example",
    ".env.local.example",
)

SKIP_NAMES = {".env", ".env.local", "check_secrets.py"}
ALLOWED_PLACEHOLDERS = {
    "your-key-here",
    "your-key",
    "replace-with-strong-random-api-key",
    "replace-with-strong-random-secret",
    "test-key",
    "secret-test-key",
    "test-secret-key",
}

ENV_KEY_PATTERN = re.compile(
    r"^AZURE_OPENAI_API_KEY=([^\r\n]*)$",
    re.IGNORECASE | re.MULTILINE,
)


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCAN_DIRS:
        base = ROOT / directory
        if base.exists():
            files.extend(path for path in base.rglob("*") if path.is_file())
    for name in SCAN_FILES:
        path = ROOT / name
        if path.exists():
            files.append(path)
    return files


def main() -> int:
    violations: list[str] = []

    for path in _iter_files():
        if path.name in SKIP_NAMES:
            continue
        if path.suffix in {".pyc", ".db", ".log"}:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in ENV_KEY_PATTERN.finditer(text):
            value = match.group(1).strip().strip("\"'")
            if not value or value in ALLOWED_PLACEHOLDERS:
                continue
            if value.startswith("your-") or value.startswith("replace-with"):
                continue
            rel = path.relative_to(ROOT)
            violations.append(f"{rel}: AZURE_OPENAI_API_KEY must not contain real secrets")

    if violations:
        print("Secret scan failed:")
        for item in sorted(set(violations)):
            print(f"  - {item}")
        return 1

    print("Secret scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
