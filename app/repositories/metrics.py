from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.datetime_utils import utc_now
from app.models.db import HealthMetricORM


class MetricsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_bucket(self, metric: HealthMetricORM) -> HealthMetricORM:
        results = self.upsert_buckets_bulk([metric])
        return results[0]

    def upsert_buckets_bulk(self, metrics: list[HealthMetricORM]) -> list[HealthMetricORM]:
        if not metrics:
            return []

        persisted: list[HealthMetricORM] = []
        for metric in metrics:
            existing = self._session.scalar(
                select(HealthMetricORM).where(
                    HealthMetricORM.bucket_start == metric.bucket_start,
                    HealthMetricORM.bucket_end == metric.bucket_end,
                    HealthMetricORM.service == metric.service,
                )
            )
            if existing:
                existing.total_count = metric.total_count
                existing.error_count = metric.error_count
                existing.error_rate = metric.error_rate
                persisted.append(existing)
            else:
                self._session.add(metric)
                persisted.append(metric)

        try:
            self._session.commit()
            for item in persisted:
                self._session.refresh(item)
            return persisted
        except IntegrityError:
            self._session.rollback()
            return [self.upsert_bucket(metric) for metric in metrics]

    def list_trends(
        self,
        *,
        service: str | None = None,
        hours: int = 24,
        limit: int = 200,
    ) -> Sequence[HealthMetricORM]:
        since = utc_now() - timedelta(hours=hours)
        query = (
            select(HealthMetricORM)
            .where(HealthMetricORM.bucket_start >= since)
            .order_by(HealthMetricORM.bucket_start.asc())
        )
        if service:
            query = query.where(HealthMetricORM.service == service)
        return self._session.scalars(query.limit(limit)).all()
