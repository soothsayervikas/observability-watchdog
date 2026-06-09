from app.services.log_parsers import parse_file_content


def test_parse_file_stops_at_max_events() -> None:
    lines = "\n".join(
        f"2026-06-08T12:00:{idx % 60:02d}Z ERROR [svc] - error {idx}" for idx in range(20)
    )
    events, fmt, errors = parse_file_content(
        lines.encode(),
        filename="app.log",
        default_service="svc",
        max_events=5,
        max_lines=100,
    )
    assert fmt == "plain"
    assert len(events) == 5
    assert any("max event limit" in err for err in errors)
