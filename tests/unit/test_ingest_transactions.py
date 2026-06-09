from datetime import datetime

from sqlalchemy.orm import Session

from app.models.db import LogEventORM
from app.models.domain import LogLevel
from app.repositories.log_repository import LogRepository


def test_create_many_commits_all_rows(db_session: Session) -> None:
    repo = LogRepository(db_session)
    events = [
        LogEventORM(
            timestamp=datetime(2026, 6, 8, 12, 0, 0),
            level=LogLevel.ERROR.value,
            service="api",
            message="error one",
            metadata_json=None,
            ingested_at=datetime(2026, 6, 8, 12, 0, 1),
        ),
        LogEventORM(
            timestamp=datetime(2026, 6, 8, 12, 1, 0),
            level=LogLevel.ERROR.value,
            service="api",
            message="error two",
            metadata_json=None,
            ingested_at=datetime(2026, 6, 8, 12, 1, 1),
        ),
    ]
    count = repo.create_many(events, chunk_size=1)
    assert count == 2
    assert repo.count_logs() == 2
