from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.config import Settings
from app.core.ai_cache import get_cached, payload_hash, set_cached
from app.core.http_client import get_http_client
from app.core.logging import get_logger
from app.core.metrics import AI_ANALYSIS
from app.models.domain import AlertSeverity, AlertType

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an expert SRE observability analyst.
Analyze application log samples and time-series context to detect anomalies, error spikes,
and unusual patterns.

Return ONLY valid JSON matching this schema:
{
  "anomalies": [
    {
      "detected": true,
      "type": "ERROR_SPIKE|UNKNOWN_PATTERN|DATABASE|AUTH_FAILURE|LATENCY|DEPENDENCY",
      "severity": "LOW|MEDIUM|HIGH|CRITICAL",
      "title": "short alert title",
      "summary": "what happened",
      "root_cause_hint": "likely cause or next debugging step",
      "confidence": 0.0,
      "service": "optional service name when known"
    }
  ],
  "overall_assessment": "one sentence platform health summary"
}

Rules:
- Flag ERROR_SPIKE when error volume/rate indicates a spike vs baseline.
- Flag UNKNOWN_PATTERN for semantic anomalies even if rate looks normal.
- Use confidence between 0 and 1.
- If no anomaly, return {"anomalies": [], "overall_assessment": "..."}.
"""


class AIAnomalyItem(BaseModel):
    detected: bool = True
    type: str = "UNKNOWN_PATTERN"
    severity: AlertSeverity = AlertSeverity.MEDIUM
    title: str
    summary: str
    root_cause_hint: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    service: str | None = None


_SEVERITY_RANK: dict[AlertSeverity, int] = {
    AlertSeverity.LOW: 0,
    AlertSeverity.MEDIUM: 1,
    AlertSeverity.HIGH: 2,
    AlertSeverity.CRITICAL: 3,
}


def merge_severity(statistical: AlertSeverity, ai: AlertSeverity | None) -> AlertSeverity:
    """AI may escalate severity but cannot downgrade below the statistical baseline."""
    if ai is None:
        return statistical
    if _SEVERITY_RANK[ai] >= _SEVERITY_RANK[statistical]:
        return ai
    return statistical


class AIAnalysisResult(BaseModel):
    anomalies: list[AIAnomalyItem] = Field(default_factory=list)
    overall_assessment: str = ""


@dataclass(frozen=True)
class AIAnalysisOutcome:
    result: AIAnalysisResult | None
    status: Literal["disabled", "success", "failed"]
    error: str | None = None


@dataclass(frozen=True)
class AIDetectionResult:
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    window_start: datetime
    window_end: datetime
    metrics: dict[str, Any]
    dedupe_key: str


class AzureOpenAIClassifier:
    """Azure OpenAI-backed anomaly classifier for log analysis."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(
            self._settings.ai_classifier_enabled
            and self._settings.azure_openai_api_key
            and self._settings.azure_openai_deployment
        )

    def _chat_url(self) -> str:
        base = self._settings.azure_openai_endpoint.rstrip("/")
        if "/api/projects/" in base:
            base = base.split("/api/projects/")[0]
        deployment = self._settings.azure_openai_deployment
        version = self._settings.azure_openai_api_version
        return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={version}"

    async def analyze(
        self,
        *,
        error_logs: list[Any],
        bucket_summary: list[dict[str, Any]],
        statistical_findings: list[dict[str, Any]],
    ) -> AIAnalysisOutcome:
        if not self.enabled:
            AI_ANALYSIS.inc(status="disabled")
            return AIAnalysisOutcome(result=None, status="disabled")

        log_sample = [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "service": log.service,
                "message": log.message[:300],
            }
            for log in error_logs[: self._settings.ai_max_log_samples]
        ]

        user_payload = {
            "task": "Detect log anomalies and error spikes for an observability watchdog.",
            "bucket_metrics": bucket_summary[-self._settings.ai_max_buckets :],
            "statistical_findings": statistical_findings,
            "error_log_sample": log_sample,
        }

        cache_key = payload_hash(user_payload)
        cached = get_cached(cache_key, ttl_seconds=self._settings.ai_cache_ttl_seconds)
        if cached is not None:
            logger.info("AI analysis cache hit")
            AI_ANALYSIS.inc(status="success")
            return AIAnalysisOutcome(
                result=AIAnalysisResult.model_validate(cached),
                status="success",
            )

        try:
            timeout = self._settings.azure_openai_timeout_seconds
            client = get_http_client()
            response = await client.post(
                self._chat_url(),
                headers={
                    "api-key": self._settings.azure_openai_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": json.dumps(user_payload)},
                    ],
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                timeout=timeout,
            )
            response.raise_for_status()
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            parsed = AIAnalysisResult.model_validate(json.loads(content))
            set_cached(cache_key, parsed.model_dump())
            logger.info(
                "AI analysis complete: anomalies=%s assessment=%s",
                len(parsed.anomalies),
                parsed.overall_assessment[:120],
            )
            AI_ANALYSIS.inc(status="success")
            return AIAnalysisOutcome(result=parsed, status="success")
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("AI analysis failed: %s", exc)
            AI_ANALYSIS.inc(status="failed")
            return AIAnalysisOutcome(result=None, status="failed", error=str(exc))

    def enrich_spike(
        self,
        spike: Any,
        ai_item: AIAnomalyItem | None,
    ) -> AIDetectionResult:
        title = ai_item.title if ai_item else spike.title
        description = spike.description
        if ai_item:
            description = (
                f"{ai_item.summary} Root cause hint: {ai_item.root_cause_hint} "
                f"(AI confidence: {ai_item.confidence:.0%})"
            )

        metrics = dict(spike.metrics)
        metrics["detection_method"] = "hybrid_statistical_ai"
        if ai_item:
            metrics["ai_classification"] = ai_item.type
            metrics["ai_confidence"] = ai_item.confidence
            metrics["ai_root_cause_hint"] = ai_item.root_cause_hint

        severity = merge_severity(spike.severity, ai_item.severity if ai_item else None)
        return AIDetectionResult(
            alert_type=AlertType.ERROR_SPIKE,
            severity=severity,
            title=title,
            description=description,
            window_start=spike.window_start,
            window_end=spike.window_end,
            metrics=metrics,
            dedupe_key=spike.dedupe_key,
        )

    def to_ai_only_detection(
        self,
        item: AIAnomalyItem,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> AIDetectionResult:
        alert_type = (
            AlertType.ERROR_SPIKE if item.type == "ERROR_SPIKE" else AlertType.UNKNOWN_PATTERN
        )
        dedupe_key = f"AI:{item.type}:{window_start.isoformat()}:{item.title[:40]}"
        return AIDetectionResult(
            alert_type=alert_type,
            severity=item.severity,
            title=item.title,
            description=(
                f"{item.summary} Root cause hint: {item.root_cause_hint} "
                f"(AI confidence: {item.confidence:.0%})"
            ),
            window_start=window_start,
            window_end=window_end,
            metrics={
                "detection_method": "ai",
                "ai_classification": item.type,
                "ai_confidence": item.confidence,
                "ai_root_cause_hint": item.root_cause_hint,
            },
            dedupe_key=dedupe_key,
        )
