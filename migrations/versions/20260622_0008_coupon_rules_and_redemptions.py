"""add coupon rules and redemption report

Revision ID: 20260622_0008
Revises: 20260622_0007
Create Date: 2026-06-22 21:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0008"
down_revision: Union[str, None] = "20260622_0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("coupons") as batch_op:
        batch_op.add_column(
            sa.Column(
                "discount_type",
                sa.String(length=20),
                server_default="percent",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "discount_value",
                sa.Numeric(12, 2),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "minimum_subtotal",
                sa.Numeric(12, 2),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "per_customer_limit",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=False,
            )
        )

    op.execute("UPDATE coupons SET discount_value = discount_percent")

    op.create_table(
        "coupon_redemptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("coupon_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.String(length=50), nullable=False),
        sa.Column("customer_email", sa.String(length=200), nullable=True),
        sa.Column("customer_cpf", sa.String(length=20), nullable=True),
        sa.Column(
            "discount_amount",
            sa.Numeric(12, 2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["coupon_id"], ["coupons.id"]),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index(
        "ix_coupon_redemptions_coupon_id",
        "coupon_redemptions",
        ["coupon_id"],
        unique=False,
    )
    op.create_index(
        "ix_coupon_redemptions_order_id",
        "coupon_redemptions",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_coupon_redemptions_customer_email",
        "coupon_redemptions",
        ["customer_email"],
        unique=False,
    )
    op.create_index(
        "ix_coupon_redemptions_customer_cpf",
        "coupon_redemptions",
        ["customer_cpf"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_coupon_redemptions_customer_cpf", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_customer_email", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_order_id", table_name="coupon_redemptions")
    op.drop_index("ix_coupon_redemptions_coupon_id", table_name="coupon_redemptions")
    op.drop_table("coupon_redemptions")

    with op.batch_alter_table("coupons") as batch_op:
        batch_op.drop_column("updated_at")
        batch_op.drop_column("per_customer_limit")
        batch_op.drop_column("ends_at")
        batch_op.drop_column("starts_at")
        batch_op.drop_column("minimum_subtotal")
        batch_op.drop_column("discount_value")
        batch_op.drop_column("discount_type")
