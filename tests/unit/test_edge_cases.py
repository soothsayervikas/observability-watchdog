from datetime import datetime, timedelta

from app.services.detection.statistical import TimeBucket, detect_error_spikes
from app.services.log_parsers import parse_file_content, parse_plain_log_line


def test_fallback_parser_marks_unparsed_lines_as_info() -> None:
    event = parse_plain_log_line(
        "No ERROR occurred while processing request",
        default_service="api",
    )
    assert event is not None
    assert event.level.value == "INFO"
    assert event.metadata is not None
    assert event.metadata.get("unparsed") is True


def test_parse_invalid_utf8_returns_error() -> None:
    events, fmt, errors = parse_file_content(
        b"\xff\xfe invalid",
        filename="bad.log",
        default_service="api",
    )
    assert events == []
    assert fmt == "unknown"
    assert errors
    assert "UTF-8" in errors[0]


def test_parse_blank_file_returns_no_events() -> None:
    events, fmt, errors = parse_file_content(
        b"# comment only\n\n",
        filename="empty.log",
        default_service="api",
    )
    assert events == []
    assert fmt == "plain"
    assert errors == []


def test_detect_single_bucket_high_error_rate() -> None:
    start = datetime(2026, 6, 8, 10, 0, 0)
    bucket = TimeBucket(start, start + timedelta(minutes=5), total_count=50, error_count=20)
    results = detect_error_spikes(
        [bucket],
        baseline_buckets=6,
        z_threshold=2.5,
        min_error_count=5,
        service="api",
    )
    assert len(results) == 1
    assert results[0].metrics["error_count"] == 20
