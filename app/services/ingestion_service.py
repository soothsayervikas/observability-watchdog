from datetime import timedelta

from app.config import Settings
from app.core.datetime_utils import utc_now
from app.core.exceptions import IngestionError, IngestionParseError
from app.core.logging import get_logger
from app.core.metrics import INGEST_EVENTS
from app.models.db import LogEventORM
from app.models.domain import LogEventCreate, LogIngestResponse
from app.repositories.log_repository import LogRepository
from app.services.log_parsers import parse_file_content

logger = get_logger(__name__)


class IngestionService:
    def __init__(self, log_repo: LogRepository, settings: Settings | None = None) -> None:
        self._log_repo = log_repo
        self._settings = settings

    def _maybe_prune_old_logs(self) -> None:
        if not self._settings or self._settings.log_retention_days <= 0:
            return
        cutoff = utc_now() - timedelta(days=self._settings.log_retention_days)
        deleted = self._log_repo.delete_older_than(cutoff)
        if deleted:
            logger.info(
                "Pruned %s log events older than %s days",
                deleted,
                self._settings.log_retention_days,
            )

    def ingest(self, events: list[LogEventCreate]) -> LogIngestResponse:
        accepted_events: list[LogEventORM] = []
        errors: list[str] = []

        max_message = self._settings.effective_log_max_message_chars if self._settings else 8192
        for index, event in enumerate(events):
            try:
                if len(event.message) > max_message:
                    errors.append(
                        f"Row {index}: message exceeds max length of {max_message} characters"
                    )
                    continue
                accepted_events.append(
                    LogEventORM(
                        timestamp=event.timestamp,
                        level=event.level.value,
                        service=event.service,
                        message=event.message,
                        metadata_json=event.metadata,
                        ingested_at=utc_now(),
                    )
                )
            except Exception as exc:  # noqa: BLE001 - collect per-record failures
                errors.append(f"Row {index}: {exc}")

        if accepted_events:
            chunk_size = self._settings.log_ingest_chunk_size if self._settings else 500
            try:
                self._log_repo.create_many(accepted_events, chunk_size=chunk_size)
            except Exception as exc:
                raise IngestionError(f"Failed to persist log events: {exc}") from exc
            INGEST_EVENTS.inc(amount=len(accepted_events), result="accepted")
            logger.info("Ingested %s log events (%s rejected)", len(accepted_events), len(errors))
            self._maybe_prune_old_logs()

        if errors:
            INGEST_EVENTS.inc(amount=len(errors), result="rejected")

        return LogIngestResponse(
            accepted=len(accepted_events),
            rejected=len(errors),
            errors=errors,
        )

    def ingest_bytes(
        self,
        content: bytes,
        *,
        filename: str,
        default_service: str | None = None,
        source_type: str = "upload",
    ) -> dict:
        service = default_service or (
            self._settings.log_default_service if self._settings else "app-service"
        )
        max_events = self._settings.log_max_events_per_file if self._settings else 50_000
        max_lines = self._settings.log_max_jsonl_lines if self._settings else 100_000
        events, format_detected, parse_errors = parse_file_content(
            content,
            filename=filename,
            default_service=service,
            max_events=max_events,
            max_lines=max_lines,
        )
        if not events:
            errors = parse_errors or ["No parseable log events found"]
            raise IngestionParseError("; ".join(errors[:5]))

        result = self.ingest(events)
        combined_errors = parse_errors + result.errors
        return {
            "accepted": result.accepted,
            "rejected": result.rejected + len(parse_errors),
            "errors": combined_errors,
            "source_file": filename,
            "format_detected": format_detected,
            "source_type": source_type,
        }

    def ingest_raw_text(
        self,
        content: str,
        *,
        format_name: str,
        default_service: str | None = None,
    ) -> LogIngestResponse:
        service = default_service or (
            self._settings.log_default_service if self._settings else "app-service"
        )
        fake_name = f"stream.{format_name}"
        result = self.ingest_bytes(
            content.encode("utf-8"),
            filename=fake_name,
            default_service=service,
            source_type="stream",
        )
        return LogIngestResponse(
            accepted=result["accepted"],
            rejected=result["rejected"],
            errors=result["errors"],
        )
