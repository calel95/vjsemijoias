"""add vj admin customers

Revision ID: 20260630_0020
Revises: 20260630_0019
Create Date: 2026-06-30 14:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_0020"
down_revision: Union[str, None] = "20260630_0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("whatsapp", sa.String(length=30), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("cpf", sa.String(length=11), nullable=True),
        sa.Column("instagram", sa.String(length=120), nullable=True),
        sa.Column("cidade", sa.String(length=120), nullable=True),
        sa.Column("estado", sa.String(length=2), nullable=True),
        sa.Column("data_nascimento", sa.Date(), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("origem", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_nome", "customers", ["nome"], unique=False)
    op.create_index("ix_customers_whatsapp", "customers", ["whatsapp"], unique=False)
    op.create_index("ix_customers_email", "customers", ["email"], unique=False)
    op.create_index("ix_customers_cpf", "customers", ["cpf"], unique=False)
    op.create_index("ix_customers_instagram", "customers", ["instagram"], unique=False)
    op.create_index("ix_customers_cidade", "customers", ["cidade"], unique=False)
    op.create_index("ix_customers_origem", "customers", ["origem"], unique=False)
    op.create_index("ix_customers_status", "customers", ["status"], unique=False)
    op.create_index("ix_customers_created_by_id", "customers", ["created_by_id"], unique=False)
    op.create_index("ix_customers_updated_by_id", "customers", ["updated_by_id"], unique=False)

    with op.batch_alter_table("vj_admin_pedidos") as batch_op:
        batch_op.add_column(sa.Column("customer_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_vj_admin_pedidos_customer_id", ["customer_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_vj_admin_pedidos_customer_id_customers",
            "customers",
            ["customer_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("vj_admin_pedidos") as batch_op:
        batch_op.drop_constraint("fk_vj_admin_pedidos_customer_id_customers", type_="foreignkey")
        batch_op.drop_index("ix_vj_admin_pedidos_customer_id")
        batch_op.drop_column("customer_id")

    op.drop_index("ix_customers_updated_by_id", table_name="customers")
    op.drop_index("ix_customers_created_by_id", table_name="customers")
    op.drop_index("ix_customers_status", table_name="customers")
    op.drop_index("ix_customers_origem", table_name="customers")
    op.drop_index("ix_customers_cidade", table_name="customers")
    op.drop_index("ix_customers_instagram", table_name="customers")
    op.drop_index("ix_customers_cpf", table_name="customers")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_index("ix_customers_whatsapp", table_name="customers")
    op.drop_index("ix_customers_nome", table_name="customers")
    op.drop_table("customers")