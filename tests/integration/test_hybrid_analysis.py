from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.models.domain import AlertSeverity, AlertType
from app.services.detection.ai_classifier import AIAnalysisOutcome, AIAnalysisResult, AIAnomalyItem


def _spike_events(base: datetime) -> list[dict]:
    normal = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "INFO",
            "service": "payment-api",
            "message": "ok",
        }
        for minute in range(60, 10, -5)
        for _ in range(8)
    ]
    spike = [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "ERROR",
            "service": "payment-api",
            "message": "db timeout",
        }
        for minute in range(9, -1, -1)
        for _ in range(12)
    ]
    return normal + spike


def _stable_events(base: datetime) -> list[dict]:
    return [
        {
            "timestamp": (base - timedelta(minutes=minute)).isoformat() + "Z",
            "level": "INFO",
            "service": "auth-api",
            "message": "request ok",
        }
        for minute in range(30, -1, -1)
        for _ in range(5)
    ]


def test_hybrid_detection_enriches_spike_with_ai(client) -> None:
    base = datetime.utcnow()
    ingest = client.post("/api/v1/logs/ingest", json={"events": _spike_events(base)})
    assert ingest.status_code == 200

    ai_result = AIAnalysisResult(
        anomalies=[
            AIAnomalyItem(
                detected=True,
                type="ERROR_SPIKE",
                severity=AlertSeverity.CRITICAL,
                title="Database outage spike",
                summary="Error rate surged across payment-api",
                root_cause_hint="Check DB connection pool",
                confidence=0.95,
            )
        ],
        overall_assessment="Critical instability in payment-api",
    )

    with patch(
        "app.services.detection.ai_classifier.AzureOpenAIClassifier.analyze",
        new=AsyncMock(return_value=AIAnalysisOutcome(result=ai_result, status="success")),
    ):
        response = client.post("/api/v1/analyze/run")

    assert response.status_code == 200
    body = response.json()
    assert body["detection_method"] == "hybrid_statistical_ai"
    assert body["ai_status"] == "success"
    assert body["alerts_created"] >= 1
    assert body["ai_assessment"] == "Critical instability in payment-api"
    assert "Database outage spike" in body["alerts"][0]["title"]


def test_ai_only_unknown_pattern_creates_alert(client) -> None:
    base = datetime.utcnow()
    ingest = client.post("/api/v1/logs/ingest", json={"events": _stable_events(base)})
    assert ingest.status_code == 200

    ai_result = AIAnalysisResult(
        anomalies=[
            AIAnomalyItem(
                detected=True,
                type="UNKNOWN_PATTERN",
                severity=AlertSeverity.HIGH,
                title="Unusual auth retry pattern",
                summary="Semantic anomaly detected without statistical spike",
                root_cause_hint="Review auth middleware logs",
                confidence=0.88,
            )
        ],
        overall_assessment="Auth service shows unusual behavior",
    )

    with patch(
        "app.services.detection.ai_classifier.AzureOpenAIClassifier.analyze",
        new=AsyncMock(return_value=AIAnalysisOutcome(result=ai_result, status="success")),
    ):
        response = client.post("/api/v1/analyze/run")

    assert response.status_code == 200
    body = response.json()
    assert body["detection_method"] == "hybrid_statistical_ai"
    assert body["ai_status"] == "success"
    assert body["alerts_created"] >= 1
    assert body["alerts"][0]["alert_type"] == AlertType.UNKNOWN_PATTERN.value
    assert "Unusual auth retry pattern" in body["alerts"][0]["title"]
