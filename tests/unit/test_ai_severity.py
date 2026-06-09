from app.models.domain import AlertSeverity
from app.services.detection.ai_classifier import merge_severity


def test_merge_severity_allows_ai_escalation() -> None:
    assert merge_severity(AlertSeverity.MEDIUM, AlertSeverity.CRITICAL) == AlertSeverity.CRITICAL


def test_merge_severity_blocks_ai_downgrade() -> None:
    assert merge_severity(AlertSeverity.HIGH, AlertSeverity.LOW) == AlertSeverity.HIGH


def test_merge_severity_without_ai_returns_statistical() -> None:
    assert merge_severity(AlertSeverity.MEDIUM, None) == AlertSeverity.MEDIUM
