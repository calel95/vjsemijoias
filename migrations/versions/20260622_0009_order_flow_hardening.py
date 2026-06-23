"""harden order checkout flow

Revision ID: 20260622_0009
Revises: 20260622_0008
Create Date: 2026-06-22 22:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0009"
down_revision: Union[str, None] = "20260622_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("idempotency_key", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("public_token", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("tracking_code", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("tracking_carrier", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_unique_constraint("uq_orders_idempotency_key", ["idempotency_key"])
        batch_op.create_unique_constraint("uq_orders_public_token", ["public_token"])

    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("checkout_url", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_column("checkout_url")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_constraint("uq_orders_public_token", type_="unique")
        batch_op.drop_constraint("uq_orders_idempotency_key", type_="unique")
        batch_op.drop_column("delivered_at")
        batch_op.drop_column("shipped_at")
        batch_op.drop_column("tracking_carrier")
        batch_op.drop_column("tracking_code")
        batch_op.drop_column("public_token")
        batch_op.drop_column("idempotency_key")
