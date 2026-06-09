from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from app.db.migrations import run_migrations


def test_run_migrations_creates_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "migrated.db"
    database_url = f"sqlite:///{db_path.as_posix()}"

    run_migrations(database_url)

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"log_events", "alerts", "health_metrics", "webhook_deliveries"}.issubset(tables)

        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO log_events "
                    "(id, timestamp, level, service, message, ingested_at) "
                    "VALUES ('test-id', '2026-06-09 12:00:00', 'INFO', 'api', "
                    "'ok', '2026-06-09 12:00:01')"
                )
            )
            conn.commit()
            count = conn.execute(text("SELECT COUNT(*) FROM log_events")).scalar_one()
            assert count == 1
    finally:
        engine.dispose()
