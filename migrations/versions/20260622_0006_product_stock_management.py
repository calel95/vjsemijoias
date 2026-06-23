"""add product stock management

Revision ID: 20260622_0006
Revises: 20260622_0005
Create Date: 2026-06-22 19:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0006"
down_revision: Union[str, None] = "20260622_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("sku", sa.String(length=80), nullable=True))
        batch_op.add_column(
            sa.Column("stock_quantity", sa.Integer(), server_default="999", nullable=False)
        )
        batch_op.add_column(
            sa.Column("low_stock_alert", sa.Integer(), server_default="2", nullable=False)
        )
        batch_op.create_index("ix_products_sku", ["sku"], unique=True)

    op.execute("UPDATE products SET stock_quantity = 0 WHERE stock_status = 'out_of_stock'")

    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(
            sa.Column("stock_deducted", sa.Boolean(), server_default=sa.false(), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("stock_deducted")

    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_index("ix_products_sku")
        batch_op.drop_column("low_stock_alert")
        batch_op.drop_column("stock_quantity")
        batch_op.drop_column("sku")
