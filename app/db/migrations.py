from pathlib import Path

from alembic.config import Config

from alembic import command


def run_migrations(database_url: str) -> None:
    """Apply Alembic migrations to the configured database."""
    root = Path(__file__).resolve().parents[2]
    alembic_cfg = Config(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")
