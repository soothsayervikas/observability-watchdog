"""Initial schema with health metric bucket uniqueness.

Revision ID: 001_initial
Revises:
Create Date: 2026-06-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "log_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("level", sa.String(length=10), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("ingested_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_log_events_level", "log_events", ["level"])
    op.create_index("ix_log_events_service", "log_events", ["service"])
    op.create_index("ix_log_events_timestamp", "log_events", ["timestamp"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("alert_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(), nullable=False),
        sa.Column("window_start", sa.DateTime(), nullable=False),
        sa.Column("window_end", sa.DateTime(), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_alerts_dedupe_key"),
    )
    op.create_index("ix_alerts_detected_at", "alerts", ["detected_at"])
    op.create_index("ix_alerts_dedupe_key", "alerts", ["dedupe_key"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_status", "alerts", ["status"])

    op.create_table(
        "health_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bucket_start", sa.DateTime(), nullable=False),
        sa.Column("bucket_end", sa.DateTime(), nullable=False),
        sa.Column("service", sa.String(length=100), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("error_rate", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bucket_start",
            "bucket_end",
            "service",
            name="uq_health_metric_bucket",
        ),
    )
    op.create_index("ix_health_metrics_bucket_start", "health_metrics", ["bucket_start"])
    op.create_index("ix_health_metrics_service", "health_metrics", ["service"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("alert_id", sa.String(length=36), nullable=False),
        sa.Column("target_url", sa.String(length=500), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_webhook_deliveries_alert_id", "webhook_deliveries", ["alert_id"])


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("health_metrics")
    op.drop_table("alerts")
    op.drop_table("log_events")
