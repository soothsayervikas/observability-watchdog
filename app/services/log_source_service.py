import shutil
from pathlib import Path

from app.config import Settings
from app.core.logging import get_logger
from app.services.ingestion_service import IngestionService

logger = get_logger(__name__)


class LogSourceService:
    """Scan watch directories and ingest new log files."""

    SUPPORTED_EXTENSIONS = {".json", ".jsonl", ".ndjson", ".log", ".txt"}

    def __init__(self, settings: Settings, ingestion: IngestionService) -> None:
        self._settings = settings
        self._ingestion = ingestion

    def _ensure_dirs(self) -> None:
        for path in (
            self._settings.log_watch_dir,
            self._settings.log_processed_dir,
            self._settings.log_failed_dir,
        ):
            Path(path).mkdir(parents=True, exist_ok=True)

    def list_pending_files(self) -> list[Path]:
        watch_dir = Path(self._settings.log_watch_dir)
        if not watch_dir.exists():
            return []
        return sorted(
            [
                path
                for path in watch_dir.iterdir()
                if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ],
            key=lambda item: item.stat().st_mtime,
        )

    def scan_and_ingest(self) -> dict:
        self._ensure_dirs()
        processed_dir = Path(self._settings.log_processed_dir)
        failed_dir = Path(self._settings.log_failed_dir)

        files = self.list_pending_files()
        ingested_files = 0
        accepted_events = 0
        rejected_events = 0
        errors: list[str] = []
        file_results: list[dict] = []

        max_bytes = self._settings.effective_log_max_upload_mb * 1024 * 1024

        for file_path in files:
            try:
                size_bytes = file_path.stat().st_size
                if size_bytes > max_bytes:
                    errors.append(
                        f"{file_path.name}: file exceeds max size of "
                        f"{self._settings.effective_log_max_upload_mb} MB"
                    )
                    shutil.move(str(file_path), failed_dir / file_path.name)
                    file_results.append(
                        {
                            "filename": file_path.name,
                            "size_bytes": size_bytes,
                            "status": "failed",
                        }
                    )
                    continue

                content = file_path.read_bytes()
                result = self._ingestion.ingest_bytes(
                    content,
                    filename=file_path.name,
                    source_type="watch_dir",
                )
                accepted_events += result["accepted"]
                rejected_events += result["rejected"]
                errors.extend(result["errors"])
                parse_failed = result["accepted"] == 0 and bool(result["errors"])
                destination = (failed_dir if parse_failed else processed_dir) / file_path.name
                shutil.move(str(file_path), destination)
                if result["accepted"] > 0:
                    ingested_files += 1
                file_results.append(
                    {
                        "filename": file_path.name,
                        "size_bytes": len(content),
                        "status": "processed" if result["accepted"] > 0 else "failed",
                    }
                )
                logger.info(
                    "Scanned file %s: accepted=%s format=%s",
                    file_path.name,
                    result["accepted"],
                    result["format_detected"],
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{file_path.name}: {exc}")
                shutil.move(str(file_path), failed_dir / file_path.name)
                file_results.append(
                    {
                        "filename": file_path.name,
                        "size_bytes": file_path.stat().st_size,
                        "status": "failed",
                    }
                )

        return {
            "scanned_files": len(files),
            "ingested_files": ingested_files,
            "accepted_events": accepted_events,
            "rejected_events": rejected_events,
            "files": file_results,
            "errors": errors,
        }
