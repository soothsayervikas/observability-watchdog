from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import build_services, get_db_session
from app.models.domain import SourceFileInfo, SourceScanResponse

router = APIRouter()


@router.get("/pending", response_model=list[SourceFileInfo])
def list_pending_sources(session: Session = Depends(get_db_session)) -> list[SourceFileInfo]:
    services = build_services(session)
    files = services["log_sources"].list_pending_files()
    return [
        SourceFileInfo(
            filename=file_path.name,
            size_bytes=file_path.stat().st_size,
            status="pending",
        )
        for file_path in files
    ]


@router.post("/scan", response_model=SourceScanResponse)
def scan_log_sources(session: Session = Depends(get_db_session)) -> SourceScanResponse:
    services = build_services(session)
    result = services["log_sources"].scan_and_ingest()
    return SourceScanResponse(
        scanned_files=result["scanned_files"],
        ingested_files=result["ingested_files"],
        accepted_events=result["accepted_events"],
        rejected_events=result["rejected_events"],
        files=[SourceFileInfo(**file_info) for file_info in result["files"]],
        errors=result["errors"],
    )
