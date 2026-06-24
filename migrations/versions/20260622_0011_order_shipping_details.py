"""add order shipping details

Revision ID: 20260622_0011
Revises: 20260622_0010
Create Date: 2026-06-22 23:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0011"
down_revision: Union[str, None] = "20260622_0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("shipping_provider", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("shipping_service", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("shipping_estimated_days", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("shipping_destination_zip", sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("shipping_destination_zip")
        batch_op.drop_column("shipping_estimated_days")
        batch_op.drop_column("shipping_service")
        batch_op.drop_column("shipping_provider")
