"""add vj admin finance expenses

Revision ID: 20260630_0021
Revises: 20260630_0020
Create Date: 2026-06-30 16:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_0021"
down_revision: Union[str, None] = "20260630_0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=False),
        sa.Column("categoria", sa.String(length=120), nullable=False),
        sa.Column("valor", sa.Numeric(12, 2), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_categoria", "expenses", ["categoria"], unique=False)
    op.create_index("ix_expenses_data", "expenses", ["data"], unique=False)
    op.create_index("ix_expenses_status", "expenses", ["status"], unique=False)
    op.create_index("ix_expenses_created_by_id", "expenses", ["created_by_id"], unique=False)
    op.create_index("ix_expenses_updated_by_id", "expenses", ["updated_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_expenses_updated_by_id", table_name="expenses")
    op.drop_index("ix_expenses_created_by_id", table_name="expenses")
    op.drop_index("ix_expenses_status", table_name="expenses")
    op.drop_index("ix_expenses_data", table_name="expenses")
    op.drop_index("ix_expenses_categoria", table_name="expenses")
    op.drop_table("expenses")