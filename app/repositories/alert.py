from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.db import AlertORM
from app.models.domain import AlertStatus


class AlertRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, alert_id: str) -> AlertORM | None:
        return self._session.get(AlertORM, alert_id)

    def get_by_dedupe_key(self, dedupe_key: str) -> AlertORM | None:
        return self._session.scalar(select(AlertORM).where(AlertORM.dedupe_key == dedupe_key))

    def create(self, alert: AlertORM) -> AlertORM:
        self._session.add(alert)
        self._session.commit()
        self._session.refresh(alert)
        return alert

    def create_if_new(self, alert: AlertORM) -> AlertORM | None:
        """Insert alert; return None when dedupe_key already exists (race-safe)."""
        try:
            return self.create(alert)
        except IntegrityError:
            self._session.rollback()
            return None

    def list_alerts(
        self,
        *,
        severity: str | None = None,
        status: AlertStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AlertORM]:
        query = select(AlertORM).order_by(AlertORM.detected_at.desc())
        if severity:
            query = query.where(AlertORM.severity == severity)
        if status:
            query = query.where(AlertORM.status == status.value)
        return self._session.scalars(query.offset(offset).limit(limit)).all()

    def count_open(self) -> int:
        return (
            self._session.scalar(
                select(func.count())
                .select_from(AlertORM)
                .where(AlertORM.status == AlertStatus.OPEN.value)
            )
            or 0
        )

    def count_open_critical(self) -> int:
        return (
            self._session.scalar(
                select(func.count())
                .select_from(AlertORM)
                .where(AlertORM.status == AlertStatus.OPEN.value, AlertORM.severity == "CRITICAL")
            )
            or 0
        )

    def count_open_high(self) -> int:
        return (
            self._session.scalar(
                select(func.count())
                .select_from(AlertORM)
                .where(AlertORM.status == AlertStatus.OPEN.value, AlertORM.severity == "HIGH")
            )
            or 0
        )

    def latest_detected_at(self) -> datetime | None:
        return self._session.scalar(select(func.max(AlertORM.detected_at)))

    def update_status(self, alert_id: str, status: AlertStatus) -> AlertORM | None:
        alert = self.get_by_id(alert_id)
        if alert is None:
            return None
        alert.status = status.value
        self._session.commit()
        self._session.refresh(alert)
        return alert
