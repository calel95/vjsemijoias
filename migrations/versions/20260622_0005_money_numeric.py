"""store money values as numeric decimals

Revision ID: 20260622_0005
Revises: 20260619_0004
Create Date: 2026-06-22 18:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0005"
down_revision: Union[str, None] = "20260619_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MONEY_TYPE = sa.Numeric(12, 2)
PERCENT_TYPE = sa.Numeric(5, 2)


def pg_cast(column: str, target_type: str) -> str:
    escaped = column.replace('"', '""')
    return f'"{escaped}"::{target_type}'


def alter_column(
    batch_op,
    column: str,
    *,
    existing_type,
    type_,
    nullable: bool,
    server_default=None,
    pg_target_type: str | None = None,
) -> None:
    kwargs = {}
    if op.get_bind().dialect.name == "postgresql" and pg_target_type:
        kwargs["postgresql_using"] = pg_cast(column, pg_target_type)
    batch_op.alter_column(
        column,
        existing_type=existing_type,
        type_=type_,
        existing_nullable=nullable,
        existing_server_default=server_default,
        **kwargs,
    )


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        alter_column(
            batch_op,
            "price",
            existing_type=sa.Float(),
            type_=MONEY_TYPE,
            nullable=False,
            pg_target_type="numeric(12, 2)",
        )
        alter_column(
            batch_op,
            "oldPrice",
            existing_type=sa.Float(),
            type_=MONEY_TYPE,
            nullable=True,
            pg_target_type="numeric(12, 2)",
        )

    with op.batch_alter_table("coupons") as batch_op:
        alter_column(
            batch_op,
            "discount_percent",
            existing_type=sa.Float(),
            type_=PERCENT_TYPE,
            nullable=False,
            server_default=sa.text("10"),
            pg_target_type="numeric(5, 2)",
        )

    with op.batch_alter_table("orders") as batch_op:
        for column in ("subtotal", "shipping", "discount", "total"):
            alter_column(
                batch_op,
                column,
                existing_type=sa.Float(),
                type_=MONEY_TYPE,
                nullable=False,
                server_default=sa.text("0") if column in {"shipping", "discount"} else None,
                pg_target_type="numeric(12, 2)",
            )


def downgrade() -> None:
    with op.batch_alter_table("orders") as batch_op:
        for column in ("subtotal", "shipping", "discount", "total"):
            alter_column(
                batch_op,
                column,
                existing_type=MONEY_TYPE,
                type_=sa.Float(),
                nullable=False,
                server_default=sa.text("0") if column in {"shipping", "discount"} else None,
                pg_target_type="double precision",
            )

    with op.batch_alter_table("coupons") as batch_op:
        alter_column(
            batch_op,
            "discount_percent",
            existing_type=PERCENT_TYPE,
            type_=sa.Float(),
            nullable=False,
            server_default=sa.text("10"),
            pg_target_type="double precision",
        )

    with op.batch_alter_table("products") as batch_op:
        alter_column(
            batch_op,
            "price",
            existing_type=MONEY_TYPE,
            type_=sa.Float(),
            nullable=False,
            pg_target_type="double precision",
        )
        alter_column(
            batch_op,
            "oldPrice",
            existing_type=MONEY_TYPE,
            type_=sa.Float(),
            nullable=True,
            pg_target_type="double precision",
        )
