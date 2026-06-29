"""add vj admin product audit fields

Revision ID: 20260629_0016
Revises: 20260629_0015
Create Date: 2026-06-29 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260629_0016"
down_revision: Union[str, None] = "20260629_0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("updated_by_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_products_created_by_id", ["created_by_id"], unique=False)
        batch_op.create_index("ix_products_updated_by_id", ["updated_by_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_products_created_by_id_users",
            "users",
            ["created_by_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_products_updated_by_id_users",
            "users",
            ["updated_by_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint("fk_products_updated_by_id_users", type_="foreignkey")
        batch_op.drop_constraint("fk_products_created_by_id_users", type_="foreignkey")
        batch_op.drop_index("ix_products_updated_by_id")
        batch_op.drop_index("ix_products_created_by_id")
        batch_op.drop_column("updated_by_id")
        batch_op.drop_column("created_by_id")
