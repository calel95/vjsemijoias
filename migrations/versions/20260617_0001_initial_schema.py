"""initial schema

Revision ID: 20260617_0001
Revises:
Create Date: 2026-06-17 00:01:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260617_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_names() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    existing_tables = table_names()

    if "products" not in existing_tables:
        op.create_table(
            "products",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("categoryName", sa.String(length=50), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("oldPrice", sa.Float(), nullable=True),
            sa.Column("image", sa.Text(), nullable=True),
            sa.Column("icon", sa.String(length=10), nullable=True),
            sa.Column("badge", sa.String(length=20), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column(
                "stock_status",
                sa.String(length=30),
                server_default="available",
                nullable=False,
            ),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("features", sa.Text(), nullable=True),
            sa.Column("custom", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("products")

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("email", sa.String(length=200), nullable=False),
            sa.Column("password_hash", sa.String(length=200), nullable=False),
            sa.Column("cpf", sa.String(length=20), nullable=True),
            sa.Column("phone", sa.String(length=30), nullable=True),
            sa.Column("birthdate", sa.String(length=20), nullable=True),
            sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
        existing_tables.add("users")

    if "newsletters" not in existing_tables:
        op.create_table(
            "newsletters",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=200), nullable=False),
            sa.Column("coupon", sa.String(length=20), server_default="VJ10", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
        existing_tables.add("newsletters")

    if "coupons" not in existing_tables:
        op.create_table(
            "coupons",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=20), nullable=False),
            sa.Column("discount_percent", sa.Float(), server_default="10", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("usage_limit", sa.Integer(), server_default="100", nullable=False),
            sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )
        existing_tables.add("coupons")

    if "product_images" not in existing_tables:
        op.create_table(
            "product_images",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("path", sa.Text(), nullable=False),
            sa.Column("position", sa.Integer(), server_default="0", nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("product_images")

    product_images_index = op.f("ix_product_images_product_id")
    if not index_exists("product_images", product_images_index):
        op.create_index(
            product_images_index,
            "product_images",
            ["product_id"],
            unique=False,
        )

    if "product_imports" not in existing_tables:
        op.create_table(
            "product_imports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("source_key", sa.String(length=255), nullable=False),
            sa.Column("source_page", sa.Integer(), nullable=True),
            sa.Column("source_folder", sa.String(length=255), nullable=True),
            sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("product_id"),
            sa.UniqueConstraint("source_key"),
        )
        existing_tables.add("product_imports")

    product_imports_index = op.f("ix_product_imports_source_key")
    if not index_exists("product_imports", product_imports_index):
        op.create_index(
            product_imports_index,
            "product_imports",
            ["source_key"],
            unique=True,
        )

    if "orders" not in existing_tables:
        op.create_table(
            "orders",
            sa.Column("id", sa.String(length=50), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("customer_name", sa.String(length=200), nullable=False),
            sa.Column("customer_email", sa.String(length=200), nullable=False),
            sa.Column("customer_cpf", sa.String(length=20), nullable=False),
            sa.Column("customer_phone", sa.String(length=30), nullable=True),
            sa.Column("address_zip", sa.String(length=20), nullable=True),
            sa.Column("address_street", sa.String(length=200), nullable=True),
            sa.Column("address_number", sa.String(length=20), nullable=True),
            sa.Column("address_complement", sa.String(length=200), nullable=True),
            sa.Column("address_neighborhood", sa.String(length=100), nullable=True),
            sa.Column("address_city", sa.String(length=100), nullable=True),
            sa.Column("address_state", sa.String(length=10), nullable=True),
            sa.Column("items", sa.Text(), nullable=False),
            sa.Column("subtotal", sa.Float(), nullable=False),
            sa.Column("shipping", sa.Float(), server_default="0", nullable=False),
            sa.Column("discount", sa.Float(), server_default="0", nullable=False),
            sa.Column("total", sa.Float(), nullable=False),
            sa.Column("payment_method", sa.String(length=50), nullable=True),
            sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
            sa.Column("coupon", sa.String(length=20), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("orders")

    if "payments" not in existing_tables:
        op.create_table(
            "payments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.String(length=50), nullable=False),
            sa.Column("provider", sa.String(length=30), server_default="infinitepay", nullable=False),
            sa.Column("provider_order_id", sa.String(length=100), nullable=True),
            sa.Column("provider_payment_id", sa.String(length=100), nullable=True),
            sa.Column("checkout_token", sa.String(length=100), nullable=False),
            sa.Column("method", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=50), server_default="pending", nullable=False),
            sa.Column("status_detail", sa.String(length=100), nullable=True),
            sa.Column("pix_qr_code", sa.Text(), nullable=True),
            sa.Column("pix_qr_code_base64", sa.Text(), nullable=True),
            sa.Column("pix_ticket_url", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("checkout_token"),
            sa.UniqueConstraint("order_id"),
            sa.UniqueConstraint("provider_order_id"),
        )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("orders")
    op.drop_index(op.f("ix_product_imports_source_key"), table_name="product_imports")
    op.drop_table("product_imports")
    op.drop_index(op.f("ix_product_images_product_id"), table_name="product_images")
    op.drop_table("product_images")
    op.drop_table("coupons")
    op.drop_table("newsletters")
    op.drop_table("users")
    op.drop_table("products")
