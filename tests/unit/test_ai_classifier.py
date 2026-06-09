import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.services.detection.ai_classifier import AzureOpenAIClassifier


@pytest.fixture
def settings() -> Settings:
    return Settings(
        ai_classifier_enabled=True,
        azure_openai_endpoint="https://test-resource.services.ai.azure.com",
        azure_openai_api_key="test-key",
        azure_openai_deployment="gpt-4.1",
    )


@pytest.mark.asyncio
async def test_ai_classifier_parses_anomaly_response(settings: Settings) -> None:
    classifier = AzureOpenAIClassifier(settings)
    mock_body = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "anomalies": [
                                {
                                    "detected": True,
                                    "type": "DATABASE",
                                    "severity": "CRITICAL",
                                    "title": "Database connection failures",
                                    "summary": "Repeated DB timeout errors detected",
                                    "root_cause_hint": "Check connection pool and DB availability",
                                    "confidence": 0.92,
                                }
                            ],
                            "overall_assessment": "Critical database instability detected",
                        }
                    )
                }
            }
        ]
    }

    mock_http_response = MagicMock()
    mock_http_response.raise_for_status = MagicMock()
    mock_http_response.json.return_value = mock_body

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_http_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        outcome = await classifier.analyze(
            error_logs=[],
            bucket_summary=[{"error_rate": 0.8, "error_count": 40, "total_count": 50}],
            statistical_findings=[],
        )

    assert outcome.status == "success"
    assert outcome.result is not None
    assert len(outcome.result.anomalies) == 1
    assert outcome.result.anomalies[0].type == "DATABASE"
    assert outcome.result.overall_assessment.startswith("Critical")


def test_chat_url_strips_project_path(settings: Settings) -> None:
    settings.azure_openai_endpoint = (
        "https://test-resource.services.ai.azure.com/api/projects/test-project"
    )
    classifier = AzureOpenAIClassifier(settings)
    url = classifier._chat_url()
    assert "/api/projects/" not in url
    assert "openai/deployments/gpt-4.1/chat/completions" in url
