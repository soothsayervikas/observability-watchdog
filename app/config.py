from functools import lru_cache
from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.exceptions import ConfigurationError

_LOCAL_ENVS = {"local", "development", "dev"}
_PRODUCTION_ENVS = {"production", "prod"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "observability-watchdog"
    app_env: str = "local"
    log_level: str = "INFO"
    json_logging: bool = True
    database_url: str = "sqlite:///./data/watchdog.db"

    # auto = follow APP_ENV | relaxed = skip hardening | strict = enforce hardening
    security_profile: Literal["auto", "relaxed", "strict"] = "auto"

    detection_window_minutes: int = 5
    detection_baseline_buckets: int = 12
    detection_z_threshold: float = 2.5
    detection_min_error_count: int = 5
    detection_per_service: bool = True
    # Comma-separated levels counted as errors for spike detection (default: ERROR,FATAL).
    detection_error_levels: str = "ERROR,FATAL"

    webhook_url: str = "http://127.0.0.1:8765/webhook"
    webhook_retry_base_seconds: float = 1.0
    webhook_timeout_seconds: int = 10
    webhook_max_retries: int = 3
    webhook_hmac_secret: str = ""

    ai_classifier_enabled: bool = True
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4.1"
    azure_openai_api_version: str = "2024-08-01-preview"
    azure_openai_timeout_seconds: int = 30
    ai_max_log_samples: int = 25
    ai_max_buckets: int = 12
    ai_min_confidence: float = 0.6

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Required in production/strict when hardening is enabled (sent as X-API-Key header).
    api_key: str = ""

    analysis_lookback_hours: int = 24

    detection_min_error_rate: float = 0.2
    detection_zero_baseline_rate: float = 0.2
    detection_severity_critical_rate: float = 0.5
    detection_severity_high_rate: float = 0.25
    detection_severity_medium_rate: float = 0.1

    log_watch_dir: str = "./data/incoming"
    log_processed_dir: str = "./data/incoming/processed"
    log_failed_dir: str = "./data/incoming/failed"
    log_default_service: str = "app-service"
    log_max_upload_mb: int = 10
    log_max_raw_body_mb: int = 10
    log_max_message_chars: int = 8192
    log_max_events_per_file: int = 50_000
    log_max_jsonl_lines: int = 100_000
    log_ingest_chunk_size: int = 500
    # Delete logs older than N days on startup (0 = disabled).
    log_retention_days: int = 30

    ai_cache_ttl_seconds: int = 300

    # Optional Redis URL for distributed rate limiting (falls back to in-memory).
    redis_url: str = ""

    # Honor X-Forwarded-For for rate limiting only when behind a trusted reverse proxy.
    trusted_proxy: bool = False

    # Serve built dashboard static files from dashboard/dist (Docker / production).
    serve_dashboard: bool = False  # set SERVE_DASHBOARD=true in Docker

    rate_limit_enabled: bool = True
    rate_limit_ingest_per_minute: int = 120
    rate_limit_analyze_per_minute: int = 10
    rate_limit_default_per_minute: int = 300

    @property
    def is_local(self) -> bool:
        return self.app_env.lower() in _LOCAL_ENVS

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in _PRODUCTION_ENVS

    @property
    def is_relaxed(self) -> bool:
        if self.security_profile == "relaxed":
            return True
        if self.security_profile == "strict":
            return False
        return self.is_local

    @property
    def hardening_enabled(self) -> bool:
        return not self.is_relaxed

    @property
    def resolved_security_profile(self) -> str:
        return "relaxed" if self.is_relaxed else "strict"

    @property
    def effective_log_max_message_chars(self) -> int:
        return self.log_max_message_chars if self.hardening_enabled else 1_048_576

    @property
    def effective_log_max_raw_body_mb(self) -> int:
        return self.log_max_raw_body_mb if self.hardening_enabled else 100

    @property
    def effective_log_max_upload_mb(self) -> int:
        return self.log_max_upload_mb if self.hardening_enabled else 100

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def auth_required(self) -> bool:
        return self.hardening_enabled and bool(self.api_key.strip())

    @property
    def effective_log_max_raw_body_bytes(self) -> int:
        return self.effective_log_max_raw_body_mb * 1024 * 1024

    @property
    def effective_log_max_raw_body_chars(self) -> int:
        """Backward-compatible alias for byte limit (misnamed historically)."""
        return self.effective_log_max_raw_body_bytes

    @property
    def detection_error_level_set(self) -> set[str]:
        return {
            level.strip().upper()
            for level in self.detection_error_levels.split(",")
            if level.strip()
        }

    @field_validator("detection_error_levels")
    @classmethod
    def validate_detection_error_levels(cls, value: str) -> str:
        levels = {level.strip().upper() for level in value.split(",") if level.strip()}
        if not levels:
            raise ValueError("detection_error_levels must include at least one level")
        return value

    @model_validator(mode="after")
    def apply_environment_defaults(self) -> Self:
        fields_set = self.model_fields_set

        if self.is_relaxed:
            if "rate_limit_enabled" not in fields_set:
                self.rate_limit_enabled = False
            if "log_max_raw_body_mb" not in fields_set:
                self.log_max_raw_body_mb = 100
            if "log_max_upload_mb" not in fields_set:
                self.log_max_upload_mb = 100
            if "log_max_message_chars" not in fields_set:
                self.log_max_message_chars = 1_048_576
        elif self.is_production:
            if "rate_limit_enabled" not in fields_set:
                self.rate_limit_enabled = True

        return self

    @property
    def webhook_allow_private_hosts(self) -> bool:
        return self.is_relaxed

    def validate_for_startup(self) -> None:
        """Fail fast when production-style settings are incomplete."""
        if not self.hardening_enabled:
            return
        if not self.api_key.strip():
            raise ConfigurationError(
                "API_KEY is required when hardening is enabled (APP_ENV=production or "
                "SECURITY_PROFILE=strict). Set API_KEY in .env before starting."
            )
        if not self.webhook_hmac_secret.strip():
            raise ConfigurationError(
                "WEBHOOK_HMAC_SECRET is required when hardening is enabled. "
                "Set WEBHOOK_HMAC_SECRET in .env before starting."
            )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_for_startup()
    return settings
