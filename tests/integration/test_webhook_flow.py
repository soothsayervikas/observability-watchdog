from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


def test_analyze_dispatches_webhook_synchronously(client) -> None:
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

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.text = "ok"

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    from app.core.url_safety import PinnedWebhookTarget

    with (
        patch(
            "app.services.webhook_service.pin_webhook_target",
            return_value=PinnedWebhookTarget(
                request_url="https://93.184.216.34/alerts",
                host_header="hooks.example.com",
            ),
        ),
        patch("app.services.webhook_service.get_http_client", return_value=mock_http_client),
    ):
        analyze = client.post("/api/v1/analyze/run")
        assert analyze.status_code == 200
        body = analyze.json()
        assert body["alerts_created"] >= 1
        assert body["webhook_status"] == "completed"
        assert body["webhook_failures"] == 0

    deliveries = client.get("/api/v1/webhooks/deliveries")
    assert deliveries.status_code == 200
    delivery_body = deliveries.json()
    assert len(delivery_body) >= 1
    assert delivery_body[0]["success"] is True
    assert delivery_body[0]["status_code"] == 200
    mock_http_client.post.assert_called()
