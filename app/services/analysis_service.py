from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.core.datetime_utils import utc_now
from app.core.logging import get_logger
from app.models.db import AlertORM, HealthMetricORM
from app.models.domain import AlertStatus
from app.repositories.log_repository import AlertRepository, LogRepository, MetricsRepository
from app.services.detection.ai_classifier import (
    AIDetectionResult,
    AzureOpenAIClassifier,
)
from app.services.detection.statistical import (
    DetectionThresholds,
    SpikeDetectionResult,
    TimeBucket,
    detect_error_spikes,
)

logger = get_logger(__name__)


DetectionRecord = SpikeDetectionResult | AIDetectionResult


@dataclass(frozen=True)
class StatisticalPhaseResult:
    log_count: int
    buckets: list[TimeBucket]
    statistical_detections: list[SpikeDetectionResult]
    bucket_summary: list[dict]
    buckets_analyzed: int
    statistical_findings: list[dict[str, Any]]
    error_logs: list[Any]
    hours: int
    latest_bucket_by_service: dict[str | None, TimeBucket]


@dataclass(frozen=True)
class AiEnrichmentResult:
    detections_to_persist: list[DetectionRecord]
    detection_method: str
    ai_assessment: str | None
    ai_status: str
    ai_error: str | None = None


class AnalysisService:
    def __init__(
        self,
        settings: Settings,
        log_repo: LogRepository,
        alert_repo: AlertRepository,
        metrics_repo: MetricsRepository,
    ) -> None:
        self._settings = settings
        self._log_repo = log_repo
        self._alert_repo = alert_repo
        self._metrics_repo = metrics_repo
        self._ai = AzureOpenAIClassifier(settings)

    def _persist_buckets(
        self,
        buckets: list[TimeBucket],
        *,
        service: str | None,
    ) -> list[dict]:
        if not buckets:
            return []

        orm_rows = [
            HealthMetricORM(
                bucket_start=bucket.start,
                bucket_end=bucket.end,
                service=service,
                total_count=bucket.total_count,
                error_count=bucket.error_count,
                error_rate=bucket.error_rate,
            )
            for bucket in buckets
        ]
        self._metrics_repo.upsert_buckets_bulk(orm_rows)

        return [
            {
                "service": service,
                "start": bucket.start.isoformat(),
                "end": bucket.end.isoformat(),
                "total_count": bucket.total_count,
                "error_count": bucket.error_count,
                "error_rate": round(bucket.error_rate, 4),
            }
            for bucket in buckets
        ]

    def _detect_for_buckets(
        self,
        buckets: list[TimeBucket],
        *,
        service: str | None,
    ) -> list[SpikeDetectionResult]:
        thresholds = DetectionThresholds(
            min_error_rate=self._settings.detection_min_error_rate,
            zero_baseline_rate=self._settings.detection_zero_baseline_rate,
            severity_critical_rate=self._settings.detection_severity_critical_rate,
            severity_high_rate=self._settings.detection_severity_high_rate,
            severity_medium_rate=self._settings.detection_severity_medium_rate,
        )
        return detect_error_spikes(
            buckets,
            baseline_buckets=self._settings.detection_baseline_buckets,
            z_threshold=self._settings.detection_z_threshold,
            min_error_count=self._settings.detection_min_error_count,
            service=service,
            thresholds=thresholds,
        )

    def _run_statistical_pipeline(
        self, *, lookback_hours: int
    ) -> tuple[
        int,
        list[TimeBucket],
        list[SpikeDetectionResult],
        list[dict],
        int,
        dict[str | None, TimeBucket],
    ]:
        since = utc_now() - timedelta(hours=lookback_hours)
        window = self._settings.detection_window_minutes
        error_levels = self._settings.detection_error_level_set
        log_count = self._log_repo.count_since(since)

        statistical_detections: list[SpikeDetectionResult] = []
        bucket_summary: list[dict] = []
        buckets_analyzed = 0
        reference_buckets: list[TimeBucket] = []
        latest_bucket_by_service: dict[str | None, TimeBucket] = {}

        if self._settings.detection_per_service:
            for service in self._log_repo.list_distinct_services_since(since):
                aggregates = self._log_repo.aggregate_time_buckets_since(
                    since,
                    window_minutes=window,
                    error_levels=error_levels,
                    service=service,
                )
                service_buckets = self._log_repo.buckets_to_time_buckets(
                    aggregates, window_minutes=window
                )
                bucket_summary.extend(self._persist_buckets(service_buckets, service=service))
                buckets_analyzed += len(service_buckets)
                reference_buckets.extend(service_buckets)
                if service_buckets:
                    latest_bucket_by_service[service] = max(
                        service_buckets, key=lambda bucket: bucket.start
                    )
                statistical_detections.extend(
                    self._detect_for_buckets(service_buckets, service=service)
                )
        else:
            aggregates = self._log_repo.aggregate_time_buckets_since(
                since,
                window_minutes=window,
                error_levels=error_levels,
                service=None,
            )
            global_buckets = self._log_repo.buckets_to_time_buckets(
                aggregates, window_minutes=window
            )
            bucket_summary = self._persist_buckets(global_buckets, service=None)
            buckets_analyzed = len(global_buckets)
            reference_buckets = global_buckets
            if global_buckets:
                latest_bucket_by_service[None] = max(
                    global_buckets, key=lambda bucket: bucket.start
                )
            statistical_detections = self._detect_for_buckets(global_buckets, service=None)

        reference_buckets.sort(key=lambda bucket: bucket.start)
        return (
            log_count,
            reference_buckets,
            statistical_detections,
            bucket_summary,
            buckets_analyzed,
            latest_bucket_by_service,
        )

    def _persist_detections(
        self,
        *,
        detections_to_persist: list[DetectionRecord],
    ) -> list[AlertORM]:
        created: list[AlertORM] = []
        for detection in detections_to_persist:
            if self._alert_repo.get_by_dedupe_key(detection.dedupe_key):
                continue

            alert_type = (
                detection.alert_type.value
                if hasattr(detection.alert_type, "value")
                else detection.alert_type
            )
            severity = (
                detection.severity.value
                if hasattr(detection.severity, "value")
                else detection.severity
            )

            alert = AlertORM(
                alert_type=alert_type,
                severity=severity,
                title=detection.title,
                description=detection.description,
                detected_at=utc_now(),
                window_start=detection.window_start,
                window_end=detection.window_end,
                metrics_json=detection.metrics,
                status=AlertStatus.OPEN.value,
                dedupe_key=detection.dedupe_key,
            )
            persisted = self._alert_repo.create_if_new(alert)
            if persisted is not None:
                created.append(persisted)
        return created

    def run_statistical_phase(self, *, lookback_hours: int | None = None) -> StatisticalPhaseResult:
        if lookback_hours is not None:
            hours = lookback_hours
        else:
            hours = self._settings.analysis_lookback_hours
        error_levels = self._settings.detection_error_level_set
        since = utc_now() - timedelta(hours=hours)

        (
            log_count,
            buckets,
            statistical_detections,
            bucket_summary,
            buckets_analyzed,
            latest_bucket_by_service,
        ) = self._run_statistical_pipeline(lookback_hours=hours)

        statistical_findings = [
            {
                "type": detection.alert_type.value,
                "severity": detection.severity.value,
                "title": detection.title,
                "description": detection.description,
                "metrics": detection.metrics,
            }
            for detection in statistical_detections
        ]

        error_logs = list(
            self._log_repo.list_errors_since(
                since,
                levels=error_levels,
                limit=self._settings.ai_max_log_samples,
            )
        )

        return StatisticalPhaseResult(
            log_count=log_count,
            buckets=buckets,
            statistical_detections=statistical_detections,
            bucket_summary=bucket_summary,
            buckets_analyzed=buckets_analyzed,
            statistical_findings=statistical_findings,
            error_logs=error_logs,
            hours=hours,
            latest_bucket_by_service=latest_bucket_by_service,
        )

    async def run_ai_enrichment(self, phase: StatisticalPhaseResult) -> AiEnrichmentResult:
        return await enrich_phase_with_ai(self._settings, phase)

    def persist_analysis_results(
        self,
        phase: StatisticalPhaseResult,
        enrichment: AiEnrichmentResult,
    ) -> list[AlertORM]:
        created = self._persist_detections(detections_to_persist=enrichment.detections_to_persist)

        logger.info(
            "Analysis complete: logs=%s buckets=%s spikes=%s alerts=%s method=%s",
            phase.log_count,
            phase.buckets_analyzed,
            len(phase.statistical_detections),
            len(created),
            enrichment.detection_method,
        )
        if enrichment.ai_assessment:
            logger.info("AI assessment: %s", enrichment.ai_assessment[:300])

        return created

    async def run_analysis(
        self, *, lookback_hours: int | None = None
    ) -> tuple[list[AlertORM], int, str | None, str]:
        phase = self.run_statistical_phase(lookback_hours=lookback_hours)
        enrichment = await self.run_ai_enrichment(phase)
        created = await run_in_threadpool(self.persist_analysis_results, phase, enrichment)
        return (
            created,
            phase.buckets_analyzed,
            enrichment.ai_assessment,
            enrichment.detection_method,
        )


async def enrich_phase_with_ai(
    settings: Settings, phase: StatisticalPhaseResult
) -> AiEnrichmentResult:
    """Run AI enrichment without requiring an open database session."""
    classifier = AzureOpenAIClassifier(settings)
    outcome = await classifier.analyze(
        error_logs=phase.error_logs,
        bucket_summary=phase.bucket_summary,
        statistical_findings=phase.statistical_findings,
    )

    ai_result = outcome.result
    detection_method = "hybrid_statistical_ai" if ai_result else "statistical"
    ai_assessment = ai_result.overall_assessment if ai_result else None
    detections_to_persist: list[DetectionRecord] = []

    ai_items = ai_result.anomalies if ai_result else []
    spike_items = [item for item in ai_items if item.detected and item.type == "ERROR_SPIKE"]
    spike_ai_item = max(spike_items, key=lambda item: item.confidence) if spike_items else None

    for spike in phase.statistical_detections:
        detections_to_persist.append(classifier.enrich_spike(spike, spike_ai_item))

    latest_bucket: TimeBucket | None = None
    if phase.latest_bucket_by_service:
        latest_bucket = max(
            phase.latest_bucket_by_service.values(), key=lambda bucket: bucket.start
        )
    elif phase.buckets:
        latest_bucket = phase.buckets[-1]

    if ai_result and latest_bucket is not None:
        seen_ai_keys: set[str] = set()
        for item in ai_items:
            if not item.detected or item.confidence < settings.ai_min_confidence:
                continue
            if item.type == "ERROR_SPIKE" and phase.statistical_detections:
                continue
            ai_key = f"{item.type}:{item.title}"
            if ai_key in seen_ai_keys:
                continue
            seen_ai_keys.add(ai_key)

            item_bucket = latest_bucket
            if item.service and item.service in phase.latest_bucket_by_service:
                item_bucket = phase.latest_bucket_by_service[item.service]

            detections_to_persist.append(
                classifier.to_ai_only_detection(
                    item,
                    window_start=item_bucket.start,
                    window_end=item_bucket.end,
                )
            )

    if not detections_to_persist:
        detections_to_persist = list(phase.statistical_detections)

    return AiEnrichmentResult(
        detections_to_persist=detections_to_persist,
        detection_method=detection_method,
        ai_assessment=ai_assessment,
        ai_status=outcome.status,
        ai_error=outcome.error,
    )
