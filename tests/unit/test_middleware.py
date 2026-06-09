import os

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def _reload_settings(**env: str) -> None:
    for key, value in env.items():
        os.environ[key] = value
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_env() -> None:
    yield
    _reload_settings(
        APP_ENV="local",
        SECURITY_PROFILE="relaxed",
        API_KEY="",
        WEBHOOK_HMAC_SECRET="",
    )


def test_body_size_limit_middleware_returns_413() -> None:
    _reload_settings(
        APP_ENV="production",
        SECURITY_PROFILE="strict",
        API_KEY="test-key",
        WEBHOOK_HMAC_SECRET="test-hmac-secret",
        WEBHOOK_URL="https://hooks.example.com/webhook",
        LOG_MAX_RAW_BODY_MB="1",
    )
    app = create_app()
    oversized = "x" * (2 * 1024 * 1024)
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/logs/ingest/raw",
            headers={"X-API-Key": "test-key", "Content-Type": "application/json"},
            json={"content": oversized, "format": "plain"},
        )
    assert response.status_code == 413


def test_metrics_endpoint_is_public() -> None:
    _reload_settings(
        APP_ENV="production",
        SECURITY_PROFILE="strict",
        API_KEY="test-key",
        WEBHOOK_HMAC_SECRET="test-hmac-secret",
        WEBHOOK_URL="https://hooks.example.com/webhook",
    )
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/metrics")
    assert response.status_code == 200
    assert "watchdog_http_requests_total" in response.text


def test_readiness_endpoint_checks_database() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["database"] is True
