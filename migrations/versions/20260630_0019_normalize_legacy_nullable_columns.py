"""normalize legacy nullable columns

Revision ID: 20260630_0019
Revises: 20260629_0018
Create Date: 2026-06-30 10:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260630_0019"
down_revision: Union[str, None] = "20260629_0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NOT_NULL_COLUMNS = [
    ("coupons", "discount_percent", sa.Numeric(5, 2), 10),
    ("coupons", "is_active", sa.Boolean(), True),
    ("coupons", "usage_limit", sa.Integer(), 100),
    ("coupons", "used_count", sa.Integer(), 0),
    ("coupons", "created_at", sa.DateTime(timezone=True), sa.func.now()),
    ("newsletters", "coupon", sa.String(length=20), "VJ10"),
    ("newsletters", "created_at", sa.DateTime(timezone=True), sa.func.now()),
    ("orders", "shipping", sa.Numeric(12, 2), 0),
    ("orders", "discount", sa.Numeric(12, 2), 0),
    ("orders", "status", sa.String(length=50), "pending"),
    ("orders", "created_at", sa.DateTime(timezone=True), sa.func.now()),
    ("payments", "created_at", sa.DateTime(timezone=True), sa.func.now()),
    ("payments", "updated_at", sa.DateTime(timezone=True), sa.func.now()),
    ("product_imports", "imported_at", sa.DateTime(timezone=True), sa.func.now()),
    ("products", "custom", sa.Boolean(), False),
    ("products", "created_at", sa.DateTime(timezone=True), sa.func.now()),
    ("products", "updated_at", sa.DateTime(timezone=True), sa.func.now()),
    ("users", "is_admin", sa.Boolean(), False),
    ("users", "created_at", sa.DateTime(timezone=True), sa.func.now()),
]


def column_is_nullable(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return bool(column["nullable"])
    return False


def set_nullable(table_name: str, column_name: str, existing_type, nullable: bool) -> None:
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=existing_type,
            nullable=nullable,
        )


def backfill_nulls(table_name: str, column_name: str, existing_type, value) -> None:
    table = sa.table(table_name, sa.column(column_name, existing_type))
    op.execute(
        table.update()
        .where(table.c[column_name].is_(None))
        .values({column_name: value})
    )


def upgrade() -> None:
    for table_name, column_name, existing_type, value in NOT_NULL_COLUMNS:
        if column_is_nullable(table_name, column_name):
            backfill_nulls(table_name, column_name, existing_type, value)
            set_nullable(table_name, column_name, existing_type, nullable=False)


def downgrade() -> None:
    for table_name, column_name, existing_type, _value in reversed(NOT_NULL_COLUMNS):
        if not column_is_nullable(table_name, column_name):
            set_nullable(table_name, column_name, existing_type, nullable=True)
