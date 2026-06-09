"""Add foreign key from webhook_deliveries.alert_id to alerts.id.

Revision ID: 002_webhook_fk
Revises: 001_initial
Create Date: 2026-06-09
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002_webhook_fk"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_deliveries") as batch_op:
        batch_op.create_foreign_key(
            "fk_webhook_deliveries_alert_id",
            "alerts",
            ["alert_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("webhook_deliveries") as batch_op:
        batch_op.drop_constraint("fk_webhook_deliveries_alert_id", type_="foreignkey")
