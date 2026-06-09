from datetime import datetime, timedelta


def _create_alert(client) -> str:
    base = datetime.utcnow()
    events = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "ERROR" if minute < 8 else "INFO",
            "service": "orders-api",
            "message": "timeout" if minute < 8 else "ok",
        }
        for minute in range(25, -1, -1)
        for _ in range(10)
    ]
    client.post("/api/v1/logs/ingest", json={"events": events})
    analyze = client.post("/api/v1/analyze/run").json()
    assert analyze["alerts_created"] >= 1
    return analyze["alerts"][0]["id"]


def test_alert_status_transitions(client) -> None:
    alert_id = _create_alert(client)

    ack = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "ACKNOWLEDGED"})
    assert ack.status_code == 200
    assert ack.json()["status"] == "ACKNOWLEDGED"

    resolved = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "RESOLVED"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"

    invalid = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "OPEN"})
    assert invalid.status_code == 400
