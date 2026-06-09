from app.core.metrics import normalize_metric_path


def test_normalize_metric_path_collapses_uuid_segments() -> None:
    alert_id = "550e8400-e29b-41d4-a716-446655440000"
    path = f"/api/v1/alerts/{alert_id}"
    assert normalize_metric_path(path) == "/api/v1/alerts/:id"


def test_normalize_metric_path_preserves_static_routes() -> None:
    assert normalize_metric_path("/api/v1/analyze/run") == "/api/v1/analyze/run"
    assert normalize_metric_path("/api/v1/health") == "/api/v1/health"


def test_readiness_returns_503_when_database_unavailable(client, monkeypatch) -> None:
    def fail_execute(*_args, **_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("sqlalchemy.orm.Session.execute", fail_execute)
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "database": False}
