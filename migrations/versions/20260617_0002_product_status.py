"""add product status fields

Revision ID: 20260617_0002
Revises: 20260617_0001
Create Date: 2026-06-17 00:02:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260617_0002"
down_revision: Union[str, None] = "20260617_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def product_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "products" not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns("products")}


def upgrade() -> None:
    existing_columns = product_columns()
    if not existing_columns:
        return

    with op.batch_alter_table("products") as batch_op:
        if "is_active" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "is_active",
                    sa.Boolean(),
                    server_default=sa.true(),
                    nullable=False,
                )
            )
        if "stock_status" not in existing_columns:
            batch_op.add_column(
                sa.Column(
                    "stock_status",
                    sa.String(length=30),
                    server_default="available",
                    nullable=False,
                )
            )


def downgrade() -> None:
    existing_columns = product_columns()
    if not existing_columns:
        return

    with op.batch_alter_table("products") as batch_op:
        if "stock_status" in existing_columns:
            batch_op.drop_column("stock_status")
        if "is_active" in existing_columns:
            batch_op.drop_column("is_active")
