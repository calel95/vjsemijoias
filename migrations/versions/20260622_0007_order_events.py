"""add order events history

Revision ID: 20260622_0007
Revises: 20260622_0006
Create Date: 2026-06-22 20:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0007"
down_revision: Union[str, None] = "20260622_0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_events_order_id", "order_events", ["order_id"], unique=False)
    op.create_index("ix_order_events_created_at", "order_events", ["created_at"], unique=False)

    op.execute(
        """
        INSERT INTO order_events (order_id, event_type, status, message, metadata_json, created_at)
        SELECT id, 'order.status.' || status, status, 'Evento inicial importado do status atual', '{}', created_at
        FROM orders
        """
    )


def downgrade() -> None:
    op.drop_index("ix_order_events_created_at", table_name="order_events")
    op.drop_index("ix_order_events_order_id", table_name="order_events")
    op.drop_table("order_events")
