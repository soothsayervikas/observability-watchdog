from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class AlertSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class AlertType(StrEnum):
    ERROR_SPIKE = "ERROR_SPIKE"
    UNKNOWN_PATTERN = "UNKNOWN_PATTERN"


class LogEventCreate(BaseModel):
    timestamp: datetime
    level: LogLevel
    service: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=65_536)
    metadata: dict[str, Any] | None = None

    @field_validator("service")
    @classmethod
    def normalize_service(cls, value: str) -> str:
        return value.strip()

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        from app.config import get_settings

        max_len = get_settings().effective_log_max_message_chars
        if len(stripped) > max_len:
            raise ValueError(f"message exceeds max length of {max_len} characters")
        return stripped


class LogEventResponse(LogEventCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ingested_at: datetime


class LogIngestRequest(BaseModel):
    events: list[LogEventCreate] = Field(min_length=1, max_length=5000)


class LogIngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: list[str] = Field(default_factory=list)


class LogUploadResponse(LogIngestResponse):
    source_file: str
    format_detected: str
    source_type: str = "upload"


class LogRawIngestRequest(BaseModel):
    # Size enforced by middleware and route handler per security profile.
    content: str = Field(min_length=1)
    format: Literal["plain", "jsonl", "json"] = "plain"
    default_service: str = Field(default="app-service", min_length=1, max_length=100)


class SourceFileInfo(BaseModel):
    filename: str
    size_bytes: int
    status: str


class SourceScanResponse(BaseModel):
    scanned_files: int
    ingested_files: int
    accepted_events: int
    rejected_events: int
    files: list[SourceFileInfo]
    errors: list[str] = Field(default_factory=list)


class AlertStatusUpdate(BaseModel):
    status: AlertStatus


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    detected_at: datetime
    window_start: datetime
    window_end: datetime
    metrics: dict[str, Any]
    status: AlertStatus


class AnalyzeResponse(BaseModel):
    alerts_created: int
    alerts: list[AlertResponse]
    buckets_analyzed: int
    ai_enabled: bool = False
    ai_assessment: str | None = None
    ai_status: str = "disabled"
    ai_error: str | None = None
    detection_method: str = "statistical"
    webhook_status: str = "none"
    webhook_failures: int = 0


class HealthSummaryResponse(BaseModel):
    health_score: int
    total_logs: int
    error_count: int
    error_rate: float
    open_alerts: int
    open_critical_alerts: int
    last_analyzed_at: datetime | None


class TrendPoint(BaseModel):
    bucket_start: datetime
    bucket_end: datetime
    service: str | None
    total_count: int
    error_count: int
    error_rate: float


class TrendsResponse(BaseModel):
    points: list[TrendPoint]


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alert_id: str
    target_url: str
    payload: dict[str, Any]
    status_code: int | None
    success: bool
    attempt: int
    error_message: str | None
    delivered_at: datetime
