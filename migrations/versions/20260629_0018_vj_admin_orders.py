"""add vj admin simple orders

Revision ID: 20260629_0018
Revises: 20260629_0017
Create Date: 2026-06-29 15:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260629_0018"
down_revision: Union[str, None] = "20260629_0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vj_admin_pedidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cliente_nome", sa.String(length=200), nullable=False),
        sa.Column("cliente_whatsapp", sa.String(length=30), nullable=True),
        sa.Column("forma_pagamento", sa.String(length=30), nullable=False),
        sa.Column("parcelas", sa.Integer(), nullable=False),
        sa.Column("desconto_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("taxa_pagamento", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("lucro_estimado", sa.Numeric(12, 2), nullable=False),
        sa.Column("margem_estimada", sa.Numeric(8, 4), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vj_admin_pedidos_status", "vj_admin_pedidos", ["status"], unique=False)
    op.create_index("ix_vj_admin_pedidos_created_by_id", "vj_admin_pedidos", ["created_by_id"], unique=False)
    op.create_index("ix_vj_admin_pedidos_updated_by_id", "vj_admin_pedidos", ["updated_by_id"], unique=False)

    op.create_table(
        "vj_admin_pedido_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pedido_id", sa.Integer(), nullable=False),
        sa.Column("produto_id", sa.Integer(), nullable=False),
        sa.Column("quantidade", sa.Integer(), nullable=False),
        sa.Column("preco_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("custo_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("taxa_percentual", sa.Numeric(5, 2), nullable=False),
        sa.Column("lucro_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_item", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["pedido_id"], ["vj_admin_pedidos.id"]),
        sa.ForeignKeyConstraint(["produto_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vj_admin_pedido_items_pedido_id", "vj_admin_pedido_items", ["pedido_id"], unique=False)
    op.create_index("ix_vj_admin_pedido_items_produto_id", "vj_admin_pedido_items", ["produto_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vj_admin_pedido_items_produto_id", table_name="vj_admin_pedido_items")
    op.drop_index("ix_vj_admin_pedido_items_pedido_id", table_name="vj_admin_pedido_items")
    op.drop_table("vj_admin_pedido_items")
    op.drop_index("ix_vj_admin_pedidos_updated_by_id", table_name="vj_admin_pedidos")
    op.drop_index("ix_vj_admin_pedidos_created_by_id", table_name="vj_admin_pedidos")
    op.drop_index("ix_vj_admin_pedidos_status", table_name="vj_admin_pedidos")
    op.drop_table("vj_admin_pedidos")
