from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.deps import build_services, get_db_session
from app.config import get_settings
from app.core.exceptions import IngestionParseError
from app.models.domain import (
    LogEventResponse,
    LogIngestRequest,
    LogIngestResponse,
    LogLevel,
    LogRawIngestRequest,
    LogUploadResponse,
)

router = APIRouter()


@router.post("/ingest", response_model=LogIngestResponse)
def ingest_logs(
    payload: LogIngestRequest,
    session: Session = Depends(get_db_session),
) -> LogIngestResponse:
    services = build_services(session)
    result = services["ingestion"].ingest(payload.events)
    if result.accepted == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No events accepted",
                "errors": result.errors[:10],
            },
        )
    return result


@router.post("/ingest/raw", response_model=LogIngestResponse)
def ingest_raw_logs(
    payload: LogRawIngestRequest,
    session: Session = Depends(get_db_session),
) -> LogIngestResponse:
    settings = get_settings()
    max_chars = settings.effective_log_max_raw_body_bytes
    if len(payload.content.encode("utf-8")) > max_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Raw body exceeds {settings.effective_log_max_raw_body_mb} MB limit",
        )
    services = build_services(session)
    return services["ingestion"].ingest_raw_text(
        payload.content,
        format_name=payload.format,
        default_service=payload.default_service,
    )


@router.post("/upload", response_model=LogUploadResponse)
async def upload_log_file(
    file: UploadFile = File(...),
    default_service: str = Form(default="app-service"),
    session: Session = Depends(get_db_session),
) -> LogUploadResponse:
    services = build_services(session)
    settings = services["settings"]
    content = await file.read()
    max_mb = settings.effective_log_max_upload_mb
    max_bytes = max_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds max upload size of {max_mb} MB",
        )

    filename = file.filename or "upload.log"
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    default_service = default_service.strip()
    if not default_service or len(default_service) > 100:
        raise HTTPException(status_code=400, detail="default_service must be 1-100 characters")

    ingestion = services["ingestion"]

    def _ingest_upload() -> dict:
        return ingestion.ingest_bytes(
            content,
            filename=filename,
            default_service=default_service,
            source_type="upload",
        )

    try:
        result = await run_in_threadpool(_ingest_upload)
    except IngestionParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result["accepted"] == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "No valid log events found in file",
                "format_detected": result["format_detected"],
                "errors": result["errors"][:10],
                "hint": "Use application logs, not data/runtime/server.log (backend log).",
            },
        )
    return LogUploadResponse(**result)


@router.get("", response_model=list[LogEventResponse])
def list_logs(
    service: str | None = None,
    level: LogLevel | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db_session),
) -> list[LogEventResponse]:
    services = build_services(session)
    logs = services["log_repo"].list_logs(
        service=service,
        level=level,
        start=since,
        end=until,
        limit=limit,
        offset=offset,
    )
    return [
        LogEventResponse(
            id=log.id,
            timestamp=log.timestamp,
            level=LogLevel(log.level),
            service=log.service,
            message=log.message,
            metadata=log.metadata_json,
            ingested_at=log.ingested_at,
        )
        for log in logs
    ]
