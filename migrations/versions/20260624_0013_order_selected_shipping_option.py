"""add selected shipping option to orders

Revision ID: 20260624_0013
Revises: 20260622_0012
Create Date: 2026-06-24 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_0013"
down_revision: Union[str, None] = "20260622_0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.add_column(sa.Column("shipping_option_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("shipping_company_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("shipping_company", sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        batch_op.drop_column("shipping_company")
        batch_op.drop_column("shipping_company_id")
        batch_op.drop_column("shipping_option_id")