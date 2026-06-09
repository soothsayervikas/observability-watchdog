from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.deps import reset_db
from app.config import Settings
from app.models.db import AlertORM
from app.repositories.log_repository import WebhookRepository
from app.services.webhook_service import WebhookService


@pytest.fixture
def webhook_service() -> WebhookService:
    reset_db("sqlite:///:memory:")
    from app.api.deps import SessionLocal

    assert SessionLocal is not None
    session = SessionLocal()
    settings = Settings(
        webhook_url="http://testserver/webhook",
        webhook_max_retries=2,
        webhook_retry_base_seconds=0.01,
    )
    service = WebhookService(settings, WebhookRepository(session))
    yield service
    session.close()


def _sample_alert() -> AlertORM:
    from datetime import datetime

    return AlertORM(
        id="alert-123",
        alert_type="ERROR_SPIKE",
        severity="HIGH",
        title="Spike",
        description="Error rate increased",
        detected_at=datetime(2026, 6, 8, 12, 0, 0),
        window_start=datetime(2026, 6, 8, 11, 55, 0),
        window_end=datetime(2026, 6, 8, 12, 0, 0),
        metrics_json={"error_count": 10},
        status="OPEN",
        dedupe_key="dedupe-1",
    )


@pytest.mark.asyncio
async def test_webhook_service_records_successful_delivery(webhook_service: WebhookService) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.text = "ok"

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.webhook_service.get_http_client", return_value=mock_http_client):
        delivery = await webhook_service.dispatch_alert(_sample_alert())

    assert delivery.success is True
    assert delivery.status_code == 200
    assert delivery.attempt == 1


@pytest.mark.asyncio
async def test_webhook_service_raises_after_retries(webhook_service: WebhookService) -> None:
    from app.core.exceptions import WebhookDeliveryError

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_http_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.webhook_service.get_http_client", return_value=mock_http_client):
        with pytest.raises(WebhookDeliveryError):
            await webhook_service.dispatch_alert(_sample_alert())
