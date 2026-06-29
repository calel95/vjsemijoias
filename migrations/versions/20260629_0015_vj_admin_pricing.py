"""add vj admin suppliers and pricing

Revision ID: 20260629_0015
Revises: 20260626_0014
Create Date: 2026-06-29 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260629_0015"
down_revision: Union[str, None] = "20260626_0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MONEY_TYPE = sa.Numeric(12, 2)
RATIO_TYPE = sa.Numeric(8, 4)


PRICE_COLUMNS = [
    "preco_pix",
    "preco_debito",
    "preco_credito_vista",
    "preco_credito_2x",
    "preco_credito_3x",
    "preco_credito_4x",
    "preco_credito_5x",
    "preco_credito_6x",
    "preco_credito_7x",
    "preco_credito_8x",
    "preco_credito_9x",
    "preco_credito_10x",
    "preco_credito_11x",
    "preco_credito_12x",
]


def upgrade() -> None:
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("whatsapp", sa.String(length=30), nullable=True),
        sa.Column("instagram", sa.String(length=120), nullable=True),
        sa.Column("site", sa.String(length=255), nullable=True),
        sa.Column("observacoes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    with op.batch_alter_table("products") as batch_op:
        batch_op.add_column(sa.Column("codigo", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("fornecedor_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("material", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("banho", sa.String(length=120), nullable=True))
        batch_op.add_column(sa.Column("cor", sa.String(length=80), nullable=True))
        batch_op.add_column(
            sa.Column("custo_peca", MONEY_TYPE, nullable=False, server_default="0")
        )
        batch_op.add_column(
            sa.Column("custo_embalagem", MONEY_TYPE, nullable=False, server_default="9.34")
        )
        batch_op.add_column(
            sa.Column("custo_total", MONEY_TYPE, nullable=False, server_default="9.34")
        )
        batch_op.add_column(
            sa.Column("markup", sa.Numeric(8, 2), nullable=False, server_default="2.00")
        )
        for column in PRICE_COLUMNS:
            batch_op.add_column(sa.Column(column, MONEY_TYPE, nullable=True))
        batch_op.add_column(sa.Column("margem_pix", RATIO_TYPE, nullable=True))
        batch_op.add_column(sa.Column("lucro_pix", MONEY_TYPE, nullable=True))
        batch_op.add_column(
            sa.Column("status", sa.String(length=30), nullable=False, server_default="rascunho")
        )
        batch_op.add_column(
            sa.Column("publicado", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.create_index("ix_products_codigo", ["codigo"], unique=True)
        batch_op.create_foreign_key(
            "fk_products_fornecedor_id_suppliers",
            "suppliers",
            ["fornecedor_id"],
            ["id"],
        )

    op.execute(
        sa.text(
            """
            UPDATE products
            SET codigo = sku,
                preco_pix = price,
                status = CASE WHEN is_active THEN 'publicado' ELSE 'rascunho' END,
                publicado = is_active
            WHERE codigo IS NULL
            """
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.drop_constraint("fk_products_fornecedor_id_suppliers", type_="foreignkey")
        batch_op.drop_index("ix_products_codigo")
        batch_op.drop_column("publicado")
        batch_op.drop_column("status")
        batch_op.drop_column("lucro_pix")
        batch_op.drop_column("margem_pix")
        for column in reversed(PRICE_COLUMNS):
            batch_op.drop_column(column)
        batch_op.drop_column("markup")
        batch_op.drop_column("custo_total")
        batch_op.drop_column("custo_embalagem")
        batch_op.drop_column("custo_peca")
        batch_op.drop_column("cor")
        batch_op.drop_column("banho")
        batch_op.drop_column("material")
        batch_op.drop_column("fornecedor_id")
        batch_op.drop_column("codigo")

    op.drop_table("suppliers")
