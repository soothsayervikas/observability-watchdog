from app.core.exceptions import AlertNotFoundError, WatchdogError
from app.models.db import AlertORM
from app.models.domain import AlertResponse, AlertSeverity, AlertStatus, AlertType
from app.repositories.log_repository import AlertRepository

_VALID_TRANSITIONS: dict[AlertStatus, set[AlertStatus]] = {
    AlertStatus.OPEN: {AlertStatus.ACKNOWLEDGED, AlertStatus.RESOLVED},
    AlertStatus.ACKNOWLEDGED: {AlertStatus.RESOLVED},
    AlertStatus.RESOLVED: set(),
}


class AlertService:
    def __init__(self, alert_repo: AlertRepository) -> None:
        self._alert_repo = alert_repo

    def to_response(self, alert: AlertORM) -> AlertResponse:
        return AlertResponse(
            id=alert.id,
            alert_type=AlertType(alert.alert_type),
            severity=AlertSeverity(alert.severity),
            title=alert.title,
            description=alert.description,
            detected_at=alert.detected_at,
            window_start=alert.window_start,
            window_end=alert.window_end,
            metrics=alert.metrics_json,
            status=AlertStatus(alert.status),
        )

    def update_status(self, alert_id: str, status: AlertStatus) -> AlertResponse:
        alert = self._alert_repo.get_by_id(alert_id)
        if alert is None:
            raise AlertNotFoundError(f"Alert not found: {alert_id}")

        current = AlertStatus(alert.status)
        allowed = _VALID_TRANSITIONS.get(current, set())
        if status not in allowed:
            raise WatchdogError(f"Invalid status transition from {current.value} to {status.value}")

        updated = self._alert_repo.update_status(alert_id, status)
        if updated is None:
            raise AlertNotFoundError(f"Alert not found: {alert_id}")
        return self.to_response(updated)
