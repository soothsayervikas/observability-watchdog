import os

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter
from app.core.webhook_signing import sign_webhook_payload, verify_webhook_signature
from app.main import create_app
from app.services.detection.statistical import TimeBucket, detect_error_spikes


@pytest.fixture(autouse=True)
def _reset_env_after_security_tests() -> None:
    yield
    _reload_settings(APP_ENV="local", SECURITY_PROFILE="relaxed", API_KEY="")


def _reload_settings(**env: str) -> Settings:
    for key, value in env.items():
        os.environ[key] = value
    get_settings.cache_clear()
    return Settings()


def test_webhook_hmac_sign_and_verify() -> None:
    secret = "test-secret-key"
    payload = {"alert_id": "abc", "severity": "HIGH", "title": "Spike"}
    signature = f"sha256={sign_webhook_payload(secret, payload)}"
    assert verify_webhook_signature(secret, payload, signature)
    assert not verify_webhook_signature(secret, payload, "sha256=deadbeef")


def test_rate_limiter_blocks_excess_requests() -> None:
    limiter = InMemoryRateLimiter()
    key = "127.0.0.1"
    assert limiter.allow(key, limit=2, window_seconds=60)
    assert limiter.allow(key, limit=2, window_seconds=60)
    assert not limiter.allow(key, limit=2, window_seconds=60)


def test_detect_error_spike_includes_service_in_dedupe_key() -> None:
    from datetime import datetime, timedelta

    start = datetime(2026, 6, 8, 10, 0, 0)
    stable = [
        TimeBucket(
            start + timedelta(minutes=idx * 5),
            start + timedelta(minutes=(idx + 1) * 5),
            100,
            2,
        )
        for idx in range(6)
    ]
    spike = TimeBucket(start + timedelta(minutes=30), start + timedelta(minutes=35), 100, 40)
    results = detect_error_spikes(
        stable + [spike],
        baseline_buckets=6,
        z_threshold=2.0,
        min_error_count=5,
        service="payment-api",
    )
    assert len(results) == 1
    assert "payment-api" in results[0].dedupe_key
    assert results[0].metrics["service"] == "payment-api"


def test_demo_path_traversal_rejected() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.post("/api/v1/demo/seed", params={"dataset": "../../../.env"})
    assert response.status_code == 400


def test_local_profile_is_relaxed() -> None:
    settings = _reload_settings(APP_ENV="local", SECURITY_PROFILE="auto")
    assert settings.is_relaxed
    assert not settings.hardening_enabled
    assert settings.effective_log_max_message_chars > 8192


def test_production_profile_is_strict() -> None:
    settings = _reload_settings(APP_ENV="production", SECURITY_PROFILE="auto")
    assert not settings.is_relaxed
    assert settings.hardening_enabled


def test_production_startup_requires_api_key() -> None:
    import pytest

    from app.core.exceptions import ConfigurationError

    try:
        _reload_settings(APP_ENV="production", SECURITY_PROFILE="strict", API_KEY="")
        with pytest.raises(ConfigurationError):
            get_settings()
    finally:
        _reload_settings(APP_ENV="local", SECURITY_PROFILE="relaxed", API_KEY="")


def test_production_startup_requires_webhook_hmac_secret() -> None:
    import pytest

    from app.core.exceptions import ConfigurationError

    try:
        _reload_settings(
            APP_ENV="production",
            SECURITY_PROFILE="strict",
            API_KEY="test-key",
            WEBHOOK_HMAC_SECRET="",
        )
        with pytest.raises(ConfigurationError, match="WEBHOOK_HMAC_SECRET"):
            get_settings()
    finally:
        _reload_settings(APP_ENV="local", SECURITY_PROFILE="relaxed", API_KEY="")


def test_trusted_proxy_uses_forwarded_for() -> None:
    from starlette.requests import Request

    from app.core.rate_limit import _client_key

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"203.0.113.1, 10.0.0.1")],
        "client": ("127.0.0.1", 12345),
    }
    _reload_settings(TRUSTED_PROXY="true")
    request = Request(scope)
    assert _client_key(request) == "203.0.113.1"


def test_oversized_message_rejected_in_strict_mode() -> None:
    _reload_settings(
        APP_ENV="production",
        SECURITY_PROFILE="strict",
        API_KEY="test-key",
        WEBHOOK_HMAC_SECRET="test-hmac-secret",
        WEBHOOK_URL="https://hooks.example.com/webhook",
    )
    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/logs/ingest",
            headers={"X-API-Key": "test-key"},
            json={
                "events": [
                    {
                        "timestamp": "2026-06-08T12:00:00Z",
                        "level": "ERROR",
                        "service": "api",
                        "message": "x" * 9000,
                    }
                ]
            },
        )
    assert response.status_code == 422
    body = response.json()
    assert "message" in str(body["detail"]).lower()


def test_api_key_required_in_strict_mode_when_configured() -> None:
    _reload_settings(
        APP_ENV="production",
        SECURITY_PROFILE="strict",
        API_KEY="secret-test-key",
        WEBHOOK_HMAC_SECRET="test-hmac-secret",
        WEBHOOK_URL="https://hooks.example.com/webhook",
    )
    app = create_app()
    with TestClient(app) as client:
        denied = client.post("/api/v1/analyze/run")
        assert denied.status_code == 401

        allowed = client.post(
            "/api/v1/analyze/run",
            headers={"X-API-Key": "secret-test-key"},
        )
        assert allowed.status_code == 200

        public = client.get("/api/v1/health")
        assert public.status_code == 200


def test_local_mode_allows_requests_without_api_key() -> None:
    _reload_settings(APP_ENV="local", SECURITY_PROFILE="relaxed", API_KEY="")
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/health/summary")
        assert response.status_code == 200


def test_rate_limit_keys_are_per_endpoint() -> None:
    limiter = InMemoryRateLimiter()
    client = "203.0.113.1"
    ingest_key = f"{client}:/api/v1/logs/ingest"
    analyze_key = f"{client}:/api/v1/analyze/run"

    for _ in range(2):
        assert limiter.allow(ingest_key, limit=2, window_seconds=60)
    assert not limiter.allow(ingest_key, limit=2, window_seconds=60)
    assert limiter.allow(analyze_key, limit=2, window_seconds=60)


def test_strict_rate_limit_blocks_excess_analyze_requests() -> None:
    from app.core.rate_limit import reset_rate_limiter

    _reload_settings(
        APP_ENV="production",
        SECURITY_PROFILE="strict",
        API_KEY="secret-test-key",
        WEBHOOK_HMAC_SECRET="test-hmac-secret",
        RATE_LIMIT_ANALYZE_PER_MINUTE="2",
        WEBHOOK_URL="https://hooks.example.com/webhook",
    )
    reset_rate_limiter()
    app = create_app()
    headers = {"X-API-Key": "secret-test-key"}
    try:
        with TestClient(app) as client:
            assert client.post("/api/v1/analyze/run", headers=headers).status_code == 200
            assert client.post("/api/v1/analyze/run", headers=headers).status_code == 200
            blocked = client.post("/api/v1/analyze/run", headers=headers)
            assert blocked.status_code == 429
    finally:
        reset_rate_limiter()
        _reload_settings(APP_ENV="local", SECURITY_PROFILE="relaxed", API_KEY="")


def test_production_mode_hides_docs_and_demo() -> None:
    from app.api.v1.router import create_api_router

    prod_router = create_api_router(include_demo=False)
    paths = [route.path for route in prod_router.routes]
    assert not any("/demo" in path for path in paths)
