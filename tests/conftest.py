import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.api.deps as deps

# Isolated in-memory DB and relaxed local profile for all tests.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("SECURITY_PROFILE", "relaxed")
os.environ.setdefault("AI_CLASSIFIER_ENABLED", "false")
os.environ.setdefault("LOG_RETENTION_DAYS", "0")


@pytest.fixture(autouse=True)
def mock_outbound_webhooks(monkeypatch):
    """Avoid real HTTP in integration tests (strict CI uses a fake WEBHOOK_URL)."""
    from unittest.mock import AsyncMock, MagicMock

    from app.core.url_safety import PinnedWebhookTarget

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.text = "ok"

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=mock_response)

    def _pin_webhook(url: str, *, allow_private_hosts: bool) -> PinnedWebhookTarget:
        return PinnedWebhookTarget(request_url=url)

    monkeypatch.setattr("app.services.webhook_service.get_http_client", lambda: mock_http_client)
    monkeypatch.setattr("app.services.webhook_service.pin_webhook_target", _pin_webhook)


@pytest.fixture(autouse=True)
def reset_settings_cache():
    from app.config import get_settings
    from app.core.ai_cache import clear_ai_cache
    from app.core.analysis_lock import reset_analysis_state
    from app.core.http_client import reset_http_client
    from app.core.rate_limit import reset_rate_limiter

    clear_ai_cache()
    reset_http_client()
    reset_rate_limiter()
    reset_analysis_state()
    get_settings.cache_clear()
    yield
    clear_ai_cache()
    reset_http_client()
    reset_rate_limiter()
    reset_analysis_state()
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def isolated_database():
    database_url = os.environ["DATABASE_URL"]
    if ":memory:" in database_url:
        deps.reset_db(database_url)
    else:
        deps.init_db(database_url)
    yield


@pytest.fixture
def client() -> TestClient:
    from app.config import get_settings
    from app.main import app

    settings = get_settings()
    headers = {"X-API-Key": settings.api_key} if settings.auth_required else {}
    with TestClient(app, headers=headers) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Session:
    deps.reset_db(os.environ["DATABASE_URL"])
    assert deps.SessionLocal is not None
    session = deps.SessionLocal()
    try:
        yield session
    finally:
        session.close()
