from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.models.db import LogEventORM
from app.models.domain import LogLevel
from app.services.detection.statistical import TimeBucket


class LogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_many(self, events: list[LogEventORM], *, chunk_size: int = 500) -> int:
        if not events:
            return 0

        try:
            for offset in range(0, len(events), chunk_size):
                chunk = events[offset : offset + chunk_size]
                self._session.add_all(chunk)
                self._session.flush()
            self._session.commit()
            return len(events)
        except Exception:
            self._session.rollback()
            raise

    def list_logs(
        self,
        *,
        service: str | None = None,
        level: LogLevel | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[LogEventORM]:
        query = select(LogEventORM).order_by(LogEventORM.timestamp.desc())
        if service:
            query = query.where(LogEventORM.service == service)
        if level:
            query = query.where(LogEventORM.level == level.value)
        if start:
            query = query.where(LogEventORM.timestamp >= start)
        if end:
            query = query.where(LogEventORM.timestamp <= end)
        return self._session.scalars(query.offset(offset).limit(limit)).all()

    def count_logs(self) -> int:
        return self._session.scalar(select(func.count()).select_from(LogEventORM)) or 0

    def count_logs_since(self, since: datetime) -> int:
        return self.count_since(since)

    def count_errors(self, *, levels: set[str] | None = None) -> int:
        error_levels = levels or {LogLevel.ERROR.value, LogLevel.FATAL.value}
        return (
            self._session.scalar(
                select(func.count())
                .select_from(LogEventORM)
                .where(LogEventORM.level.in_(sorted(error_levels)))
            )
            or 0
        )

    def count_errors_since(self, since: datetime, *, levels: set[str]) -> int:
        return (
            self._session.scalar(
                select(func.count())
                .select_from(LogEventORM)
                .where(
                    LogEventORM.timestamp >= since,
                    LogEventORM.level.in_(sorted(levels)),
                )
            )
            or 0
        )

    def delete_older_than(self, cutoff: datetime) -> int:
        result = self._session.execute(delete(LogEventORM).where(LogEventORM.timestamp < cutoff))
        self._session.commit()
        return result.rowcount or 0

    def list_since(self, since: datetime) -> Sequence[LogEventORM]:
        return self._session.scalars(
            select(LogEventORM)
            .where(LogEventORM.timestamp >= since)
            .order_by(LogEventORM.timestamp.asc())
        ).all()

    def count_since(self, since: datetime) -> int:
        return (
            self._session.scalar(
                select(func.count()).select_from(LogEventORM).where(LogEventORM.timestamp >= since)
            )
            or 0
        )

    def list_distinct_services_since(self, since: datetime) -> list[str]:
        rows = self._session.scalars(
            select(LogEventORM.service)
            .where(LogEventORM.timestamp >= since)
            .distinct()
            .order_by(LogEventORM.service)
        ).all()
        return list(rows)

    def aggregate_time_buckets_since(
        self,
        since: datetime,
        *,
        window_minutes: int,
        error_levels: set[str],
        service: str | None = None,
    ) -> list[tuple[datetime, int, int]]:
        """Aggregate log counts into wall-clock buckets in SQL (avoids loading all rows)."""
        if window_minutes <= 0:
            return []

        level_list = sorted(error_levels)
        if not level_list:
            return []

        level_sql = ", ".join(f"'{level}'" for level in level_list)
        params: dict[str, object] = {"since": since, "window": window_minutes}
        service_filter = ""
        if service is not None:
            service_filter = " AND service = :service"
            params["service"] = service

        query = text(
            f"""
            SELECT
              datetime(
                strftime('%Y-%m-%d %H:', timestamp) ||
                printf(
                  '%02d:00',
                  (CAST(strftime('%M', timestamp) AS INTEGER) / :window) * :window
                )
              ) AS bucket_start,
              COUNT(*) AS total_count,
              SUM(CASE WHEN level IN ({level_sql}) THEN 1 ELSE 0 END) AS error_count
            FROM log_events
            WHERE timestamp >= :since
            {service_filter}
            GROUP BY bucket_start
            HAVING COUNT(*) > 0
            ORDER BY bucket_start
            """
        )
        rows = self._session.execute(query, params).all()
        buckets: list[tuple[datetime, int, int]] = []
        for row in rows:
            bucket_start = datetime.strptime(str(row.bucket_start), "%Y-%m-%d %H:%M:%S")
            buckets.append((bucket_start, int(row.total_count), int(row.error_count)))
        return buckets

    @staticmethod
    def buckets_to_time_buckets(
        aggregates: list[tuple[datetime, int, int]],
        *,
        window_minutes: int,
    ) -> list[TimeBucket]:
        window = timedelta(minutes=window_minutes)
        return [
            TimeBucket(
                start=bucket_start,
                end=bucket_start + window,
                total_count=total_count,
                error_count=error_count,
            )
            for bucket_start, total_count, error_count in aggregates
        ]

    def list_bucket_fields_since(
        self, since: datetime, *, service: str | None = None
    ) -> Sequence[tuple[datetime, str, str]]:
        query = (
            select(LogEventORM.timestamp, LogEventORM.level, LogEventORM.service)
            .where(LogEventORM.timestamp >= since)
            .order_by(LogEventORM.timestamp.asc())
        )
        if service:
            query = query.where(LogEventORM.service == service)
        rows = self._session.execute(query).all()
        return [(row[0], row[1], row[2]) for row in rows]

    def list_errors_since(
        self, since: datetime, *, levels: set[str], limit: int
    ) -> Sequence[LogEventORM]:
        return self._session.scalars(
            select(LogEventORM)
            .where(
                LogEventORM.timestamp >= since,
                LogEventORM.level.in_(sorted(levels)),
            )
            .order_by(LogEventORM.timestamp.asc())
            .limit(limit)
        ).all()
