import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import build_services, get_db_session
from app.models.domain import LogEventCreate, LogIngestResponse

router = APIRouter()
SAMPLES_DIR = Path(__file__).resolve().parents[3] / "data" / "samples"
_DATASET_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _resolve_sample_path(dataset: str) -> Path:
    if not _DATASET_PATTERN.match(dataset):
        raise HTTPException(status_code=400, detail="Invalid dataset name")

    sample_path = (SAMPLES_DIR / f"{dataset}.json").resolve()
    samples_root = SAMPLES_DIR.resolve()
    if not sample_path.is_relative_to(samples_root):
        raise HTTPException(status_code=400, detail="Invalid dataset path")

    return sample_path


@router.post("/seed", response_model=LogIngestResponse)
def seed_sample_data(
    dataset: str = "error_spike",
    session: Session = Depends(get_db_session),
) -> LogIngestResponse:
    sample_path = _resolve_sample_path(dataset)
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail=f"Sample dataset not found: {dataset}")

    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    events = [LogEventCreate.model_validate(item) for item in payload["events"]]
    services = build_services(session)
    return services["ingestion"].ingest(events)
