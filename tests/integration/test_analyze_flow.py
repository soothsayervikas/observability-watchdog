from datetime import datetime


def test_health_endpoint(client) -> None:
    from app.config import get_settings

    settings = get_settings()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    if settings.hardening_enabled:
        assert body == {"status": "ok"}
    else:
        assert "environment" in body
        assert "hardening_enabled" in body


def test_ingest_and_analyze_flow(client) -> None:
    from datetime import timedelta

    base = datetime.utcnow()
    normal_events = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "INFO",
            "service": "payment-api",
            "message": "ok",
        }
        for minute in range(60, 10, -5)
        for _ in range(8)
    ]
    spike_events = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "ERROR",
            "service": "payment-api",
            "message": "db timeout",
        }
        for minute in range(9, -1, -1)
        for _ in range(12)
    ]

    events = normal_events + spike_events
    ingest = client.post("/api/v1/logs/ingest", json={"events": events})
    assert ingest.status_code == 200
    assert ingest.json()["accepted"] == len(events)

    analyze = client.post("/api/v1/analyze/run")
    assert analyze.status_code == 200
    body = analyze.json()
    assert body["buckets_analyzed"] >= 1
    assert body["alerts_created"] >= 1
    assert body["detection_method"] == "statistical"

    summary = client.get("/api/v1/health/summary")
    assert summary.status_code == 200
    assert summary.json()["open_alerts"] >= 1


def test_analyze_dedupes_repeat_runs(client) -> None:
    from datetime import timedelta

    base = datetime.utcnow()
    events = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "ERROR" if minute < 10 else "INFO",
            "service": "billing-api",
            "message": "payment failed" if minute < 10 else "ok",
        }
        for minute in range(30, -1, -1)
        for _ in range(10)
    ]
    ingest = client.post("/api/v1/logs/ingest", json={"events": events})
    assert ingest.status_code == 200

    first = client.post("/api/v1/analyze/run").json()
    second = client.post("/api/v1/analyze/run").json()

    assert first["alerts_created"] >= 1
    assert second["alerts_created"] == 0


def test_ingest_all_rejected_returns_400(client, monkeypatch) -> None:
    from app.models.domain import LogIngestResponse

    monkeypatch.setattr(
        "app.api.v1.logs.build_services",
        lambda session: {
            "ingestion": type(
                "IngestionStub",
                (),
                {
                    "ingest": staticmethod(
                        lambda events: LogIngestResponse(
                            accepted=0, rejected=len(events), errors=["simulated rejection"]
                        )
                    )
                },
            )()
        },
    )

    response = client.post(
        "/api/v1/logs/ingest",
        json={
            "events": [
                {
                    "timestamp": "2026-06-09T12:00:00Z",
                    "level": "INFO",
                    "service": "api",
                    "message": "ok",
                }
            ]
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "No events accepted"
