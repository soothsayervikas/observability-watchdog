from datetime import timedelta

from app.config import Settings
from app.core.datetime_utils import utc_now
from app.models.db import HealthMetricORM
from app.repositories.log_repository import AlertRepository, LogRepository, MetricsRepository
from app.services.detection.statistical import compute_health_score


class MetricsService:
    def __init__(
        self,
        log_repo: LogRepository,
        alert_repo: AlertRepository,
        metrics_repo: MetricsRepository,
        settings: Settings,
    ) -> None:
        self._log_repo = log_repo
        self._alert_repo = alert_repo
        self._metrics_repo = metrics_repo
        self._settings = settings

    def health_summary(self) -> dict:
        error_levels = self._settings.detection_error_level_set
        since = utc_now() - timedelta(hours=self._settings.analysis_lookback_hours)
        total_logs = self._log_repo.count_logs_since(since)
        error_count = self._log_repo.count_errors_since(since, levels=error_levels)
        error_rate = (error_count / total_logs) if total_logs else 0.0
        open_alerts = self._alert_repo.count_open()
        open_critical = self._alert_repo.count_open_critical()

        open_high = self._alert_repo.count_open_high()
        recent_spikes = sum(
            1
            for alert in self._alert_repo.list_alerts(limit=100)
            if alert.detected_at >= utc_now() - timedelta(hours=1)
        )

        return {
            "health_score": compute_health_score(
                error_rate=error_rate,
                open_critical_alerts=open_critical,
                open_high_alerts=open_high,
                recent_spike_count=recent_spikes,
            ),
            "total_logs": total_logs,
            "error_count": error_count,
            "error_rate": round(error_rate, 4),
            "open_alerts": open_alerts,
            "open_critical_alerts": open_critical,
            "last_analyzed_at": self._alert_repo.latest_detected_at(),
        }

    def trends(self, *, service: str | None = None, hours: int = 24) -> list[HealthMetricORM]:
        return list(self._metrics_repo.list_trends(service=service, hours=hours))
