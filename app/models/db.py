import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.core.datetime_utils import utc_now


class Base(DeclarativeBase):
    pass


class LogEventORM(Base):
    __tablename__ = "log_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    level: Mapped[str] = mapped_column(String(10), index=True)
    service: Mapped[str] = mapped_column(String(100), index=True)
    message: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class AlertORM(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime)
    window_end: Mapped[datetime] = mapped_column(DateTime)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    dedupe_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)


class HealthMetricORM(Base):
    __tablename__ = "health_metrics"
    __table_args__ = (
        UniqueConstraint(
            "bucket_start",
            "bucket_end",
            "service",
            name="uq_health_metric_bucket",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime, index=True)
    bucket_end: Mapped[datetime] = mapped_column(DateTime)
    service: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    total_count: Mapped[int] = mapped_column(Integer)
    error_count: Mapped[int] = mapped_column(Integer)
    error_rate: Mapped[float] = mapped_column(Float)


class WebhookDeliveryORM(Base):
    __tablename__ = "webhook_deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("alerts.id", ondelete="CASCADE"), index=True
    )
    target_url: Mapped[str] = mapped_column(String(500))
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


def create_db_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine_kwargs: dict[str, Any] = {"connect_args": connect_args}
    if database_url.endswith(":memory:") or database_url.rstrip("/").endswith(":memory:"):
        from sqlalchemy.pool import StaticPool

        engine_kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **engine_kwargs)


def create_session_factory(database_url: str) -> tuple[sessionmaker[Session], Engine]:
    engine = create_db_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False), engine
