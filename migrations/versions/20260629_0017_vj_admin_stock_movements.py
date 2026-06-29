"""add vj admin stock movements

Revision ID: 20260629_0017
Revises: 20260629_0016
Create Date: 2026-06-29 14:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260629_0017"
down_revision: Union[str, None] = "20260629_0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("saldo_anterior", sa.Integer(), nullable=False),
        sa.Column("saldo_atual", sa.Integer(), nullable=False),
        sa.Column("motivo", sa.String(length=200), nullable=False),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["produto_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_movements_produto_id", "stock_movements", ["produto_id"], unique=False)
    op.create_index("ix_stock_movements_tipo", "stock_movements", ["tipo"], unique=False)
    op.create_index("ix_stock_movements_created_by_id", "stock_movements", ["created_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_stock_movements_created_by_id", table_name="stock_movements")
    op.drop_index("ix_stock_movements_tipo", table_name="stock_movements")
    op.drop_index("ix_stock_movements_produto_id", table_name="stock_movements")
    op.drop_table("stock_movements")
