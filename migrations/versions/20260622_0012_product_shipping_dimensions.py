"""add product shipping dimensions

Revision ID: 20260622_0012
Revises: 20260622_0011
Create Date: 2026-06-22 23:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0012"
down_revision: Union[str, None] = "20260622_0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(
            sa.Column("weight_grams", sa.Integer(), nullable=False, server_default="100")
        )
        batch_op.add_column(
            sa.Column("height_cm", sa.Numeric(6, 2), nullable=False, server_default="2.00")
        )
        batch_op.add_column(
            sa.Column("width_cm", sa.Numeric(6, 2), nullable=False, server_default="10.00")
        )
        batch_op.add_column(
            sa.Column("length_cm", sa.Numeric(6, 2), nullable=False, server_default="15.00")
        )
        batch_op.add_column(
            sa.Column(
                "shipping_profile",
                sa.String(length=50),
                nullable=False,
                server_default="default",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_column("shipping_profile")
        batch_op.drop_column("length_cm")
        batch_op.drop_column("width_cm")
        batch_op.drop_column("height_cm")
        batch_op.drop_column("weight_grams")
