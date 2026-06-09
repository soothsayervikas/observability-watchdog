import json

from app.services.log_parsers import parse_file_content, parse_plain_log_line


def test_parse_python_logging_line() -> None:
    event = parse_plain_log_line(
        "2026-06-08 12:47:04 [INFO] app.main: HTTP GET /api/v1/health -> 200",
        default_service="fallback",
    )
    assert event is not None
    assert event.level.value == "INFO"
    assert event.service == "app"
    assert "HTTP GET" in event.message


def test_parse_plain_log_line() -> None:
    event = parse_plain_log_line(
        "2026-06-08T12:03:00Z ERROR [payment-api] - Database connection timeout",
        default_service="fallback",
    )
    assert event is not None
    assert event.level.value == "ERROR"
    assert event.service == "payment-api"
    assert "timeout" in event.message


def test_parse_json_file() -> None:
    payload = {
        "events": [
            {
                "timestamp": "2026-06-08T12:00:00Z",
                "level": "ERROR",
                "service": "auth-api",
                "message": "Invalid token",
            }
        ]
    }
    events, fmt, errors = parse_file_content(
        json.dumps(payload).encode(),
        filename="app.json",
        default_service="default",
    )
    assert fmt == "json"
    assert len(events) == 1
    assert events[0].service == "auth-api"
    assert errors == []


def test_parse_jsonl_file() -> None:
    lines = "\n".join(
        [
            json.dumps(
                {
                    "timestamp": "2026-06-08T12:00:00Z",
                    "level": "WARN",
                    "service": "api",
                    "message": "retrying",
                }
            ),
            json.dumps(
                {
                    "timestamp": "2026-06-08T12:01:00Z",
                    "level": "ERROR",
                    "service": "api",
                    "message": "failed",
                }
            ),
        ]
    )
    events, fmt, errors = parse_file_content(
        lines.encode(),
        filename="stream.jsonl",
        default_service="default",
    )
    assert fmt == "jsonl"
    assert len(events) == 2
    assert errors == []
