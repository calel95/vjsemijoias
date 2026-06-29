"""add product reference

Revision ID: 20260626_0014
Revises: 20260624_0013
Create Date: 2026-06-26 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260626_0014"
down_revision: Union[str, None] = "20260624_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("reference", sa.String(length=80), nullable=True))
        batch_op.create_index("ix_products_reference", ["reference"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_index("ix_products_reference")
        batch_op.drop_column("reference")