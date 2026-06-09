from pathlib import Path

import pytest

from app.config import get_settings


def test_upload_log_file(client, tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "2026-06-08T12:03:00Z ERROR [payment-api] - Database connection timeout\n",
        encoding="utf-8",
    )
    with log_file.open("rb") as handle:
        response = client.post(
            "/api/v1/logs/upload",
            files={"file": ("app.log", handle, "text/plain")},
            data={"default_service": "payment-api"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] >= 1
    assert body["format_detected"] == "plain"


def test_scan_incoming_directory(client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    watch = tmp_path / "incoming"
    processed = tmp_path / "processed"
    failed = tmp_path / "failed"
    watch.mkdir()
    processed.mkdir()
    failed.mkdir()

    monkeypatch.setenv("LOG_WATCH_DIR", str(watch))
    monkeypatch.setenv("LOG_PROCESSED_DIR", str(processed))
    monkeypatch.setenv("LOG_FAILED_DIR", str(failed))
    get_settings.cache_clear()

    sample = watch / "integration-test.log"
    sample.write_text(
        "2026-06-08T12:04:00Z ERROR [payment-api] - Timeout during scan test\n",
        encoding="utf-8",
    )

    response = client.post("/api/v1/sources/scan")
    assert response.status_code == 200
    body = response.json()
    assert body["scanned_files"] >= 1
    assert body["accepted_events"] >= 1
    assert not sample.exists()
