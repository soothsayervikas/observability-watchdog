from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from app.core.datetime_utils import utc_now
from app.models.domain import LogEventCreate, LogLevel

PLAIN_LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)"
    r"\s+(?P<level>DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)"
    r"(?:\s+\[(?P<service>[^\]]+)\])?"
    r"\s*-?\s*(?P<message>.+)$",
    re.IGNORECASE,
)

# Python logging format: 2026-06-08 12:47:04 [INFO] app.main: message
PYTHON_LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r" \[(?P<level>DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\]"
    r" (?P<logger>[^:]+): (?P<message>.+)$",
    re.IGNORECASE,
)

LEVEL_MAP = {
    "WARNING": LogLevel.WARN,
    "CRITICAL": LogLevel.FATAL,
}


def _normalize_level(raw: str) -> LogLevel:
    upper = raw.upper()
    if upper in LEVEL_MAP:
        return LEVEL_MAP[upper]
    return LogLevel(upper)


def _parse_timestamp(raw: str) -> datetime:
    value = raw.strip().replace("Z", "+00:00")
    if " " in value and "T" not in value:
        value = value.replace(" ", "T", 1)
    return datetime.fromisoformat(value)


def _event_from_dict(data: dict[str, Any], *, default_service: str) -> LogEventCreate:
    level_raw = data.get("level") or data.get("severity") or "INFO"
    service = data.get("service") or data.get("app") or data.get("source") or default_service
    message = data.get("message") or data.get("msg") or data.get("text") or ""
    timestamp_raw = data.get("timestamp") or data.get("@timestamp") or data.get("time")
    if not message:
        raise ValueError("missing message field")

    timestamp = _parse_timestamp(timestamp_raw) if timestamp_raw else utc_now()
    metadata = data.get("metadata") or {
        k: v
        for k, v in data.items()
        if k
        not in {
            "timestamp",
            "@timestamp",
            "time",
            "level",
            "severity",
            "service",
            "app",
            "source",
            "message",
            "msg",
            "text",
            "metadata",
        }
    }
    return LogEventCreate(
        timestamp=timestamp,
        level=_normalize_level(str(level_raw)),
        service=str(service),
        message=str(message),
        metadata=metadata or None,
    )


def _from_plain_match(
    match: re.Match[str], *, default_service: str, raw_line: str
) -> LogEventCreate:
    groups = match.groupdict()
    return LogEventCreate(
        timestamp=_parse_timestamp(groups["timestamp"]),
        level=_normalize_level(groups["level"]),
        service=groups.get("service") or default_service,
        message=groups["message"].strip(),
        metadata={"raw_line": raw_line},
    )


def _from_python_log_match(
    match: re.Match[str], *, default_service: str, raw_line: str
) -> LogEventCreate:
    groups = match.groupdict()
    logger_name = groups["logger"]
    service = logger_name.split(".")[0] if logger_name else default_service
    return LogEventCreate(
        timestamp=_parse_timestamp(groups["timestamp"]),
        level=_normalize_level(groups["level"]),
        service=service or default_service,
        message=groups["message"].strip(),
        metadata={"raw_line": raw_line, "logger": logger_name, "parser": "python_logging"},
    )


def parse_plain_log_line(line: str, *, default_service: str) -> LogEventCreate | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    for pattern, parser in (
        (PLAIN_LOG_PATTERN, _from_plain_match),
        (PYTHON_LOG_PATTERN, _from_python_log_match),
    ):
        match = pattern.match(stripped)
        if match:
            return parser(match, default_service=default_service, raw_line=stripped)

    return LogEventCreate(
        timestamp=utc_now(),
        level=LogLevel.INFO,
        service=default_service,
        message=stripped,
        metadata={"raw_line": stripped, "parser": "fallback", "unparsed": True},
    )


def parse_file_content(
    content: bytes,
    *,
    filename: str,
    default_service: str,
    max_events: int = 50_000,
    max_lines: int = 100_000,
) -> tuple[list[LogEventCreate], str, list[str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        return [], "unknown", [f"Invalid UTF-8 content: {exc}"]

    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    errors: list[str] = []
    events: list[LogEventCreate] = []
    limits = {"max_events": max_events, "max_lines": max_lines}

    if extension in {"jsonl", "ndjson"} or (
        extension not in {"json", "log", "txt"} and _looks_like_jsonl(text)
    ):
        events, errors = _parse_jsonl(text, default_service=default_service, **limits)
        return events, "jsonl", errors

    if extension == "json" or (
        extension not in {"log", "txt", "jsonl", "ndjson"} and text.lstrip().startswith("{")
    ):
        events, errors = _parse_json_document(text, default_service=default_service, **limits)
        return events, "json", errors

    events, errors = _parse_plain_lines(text, default_service=default_service, **limits)
    return events, "plain", errors


def _looks_like_jsonl(text: str) -> bool:
    for line in text.splitlines()[:5]:
        stripped = line.strip()
        if stripped and not stripped.startswith("{"):
            return False
    return bool(text.strip())


def _parse_json_document(
    text: str,
    *,
    default_service: str,
    max_events: int,
    max_lines: int,
) -> tuple[list[LogEventCreate], list[str]]:
    errors: list[str] = []
    events: list[LogEventCreate] = []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [], [f"Invalid JSON: {exc}"]
    rows = payload.get("events", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("JSON document must be an array or contain an 'events' array")

    if len(rows) > max_events:
        errors.append(f"JSON document exceeds max event limit of {max_events}")
        rows = rows[:max_events]

    for index, row in enumerate(rows):
        try:
            events.append(_event_from_dict(row, default_service=default_service))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"json row {index}: {exc}")
    return events, errors


def _parse_jsonl(
    text: str,
    *,
    default_service: str,
    max_events: int,
    max_lines: int,
) -> tuple[list[LogEventCreate], list[str]]:
    errors: list[str] = []
    events: list[LogEventCreate] = []
    lines = text.splitlines()
    if len(lines) > max_lines:
        errors.append(f"JSONL exceeds max line limit of {max_lines}")
        lines = lines[:max_lines]

    for index, line in enumerate(lines, start=1):
        if len(events) >= max_events:
            errors.append(f"Stopped at max event limit of {max_events}")
            break
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
            if not isinstance(row, dict):
                raise ValueError("each JSONL line must be a JSON object")
            events.append(_event_from_dict(row, default_service=default_service))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"jsonl line {index}: {exc}")
    return events, errors


def _parse_plain_lines(
    text: str,
    *,
    default_service: str,
    max_events: int,
    max_lines: int,
) -> tuple[list[LogEventCreate], list[str]]:
    errors: list[str] = []
    events: list[LogEventCreate] = []
    lines = text.splitlines()
    if len(lines) > max_lines:
        errors.append(f"Log file exceeds max line limit of {max_lines}")
        lines = lines[:max_lines]

    for index, line in enumerate(lines, start=1):
        if len(events) >= max_events:
            errors.append(f"Stopped at max event limit of {max_events}")
            break
        try:
            event = parse_plain_log_line(line, default_service=default_service)
            if event:
                events.append(event)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"plain line {index}: {exc}")
    return events, errors
