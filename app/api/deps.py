from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.models.db import Base, create_session_factory
from app.repositories.log_repository import (
    AlertRepository,
    LogRepository,
    MetricsRepository,
    WebhookRepository,
)
from app.services.alert_service import AlertService
from app.services.analysis_service import AnalysisService
from app.services.ingestion_service import IngestionService
from app.services.log_source_service import LogSourceService
from app.services.metrics_service import MetricsService
from app.services.webhook_service import WebhookService

SessionLocal: sessionmaker[Session] | None = None


def init_db(database_url: str) -> None:
    global SessionLocal
    session_factory, engine = create_session_factory(database_url)
    if ":memory:" in database_url:
        Base.metadata.create_all(bind=engine)
    else:
        from app.db.migrations import run_migrations

        run_migrations(database_url)
    SessionLocal = session_factory


def reset_db(database_url: str) -> None:
    """Drop and recreate schema — used by tests for isolation."""
    global SessionLocal
    session_factory, engine = create_session_factory(database_url)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    SessionLocal = session_factory


def get_db_session() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def build_services(session: Session, settings: Settings | None = None):
    settings = settings or get_settings()
    log_repo = LogRepository(session)
    alert_repo = AlertRepository(session)
    metrics_repo = MetricsRepository(session)
    webhook_repo = WebhookRepository(session)

    ingestion = IngestionService(log_repo, settings)
    return {
        "settings": settings,
        "ingestion": ingestion,
        "log_sources": LogSourceService(settings, ingestion),
        "analysis": AnalysisService(settings, log_repo, alert_repo, metrics_repo),
        "alerts": AlertService(alert_repo),
        "webhook": WebhookService(settings, webhook_repo),
        "metrics": MetricsService(log_repo, alert_repo, metrics_repo, settings),
        "log_repo": log_repo,
        "alert_repo": alert_repo,
        "webhook_repo": webhook_repo,
    }
