"""add admin audit logs

Revision ID: 20260619_0004
Revises: 20260617_0003
Create Date: 2026-06-19 12:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260619_0004"
down_revision: Union[str, None] = "20260617_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "admin_audit_logs" in inspector.get_table_names():
        return

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource", sa.String(length=100), nullable=True),
        sa.Column("resource_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_audit_logs_admin_user_id"),
        "admin_audit_logs",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_audit_logs_action"),
        "admin_audit_logs",
        ["action"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "admin_audit_logs" in inspector.get_table_names():
        op.drop_index(op.f("ix_admin_audit_logs_action"), table_name="admin_audit_logs")
        op.drop_index(
            op.f("ix_admin_audit_logs_admin_user_id"),
            table_name="admin_audit_logs",
        )
        op.drop_table("admin_audit_logs")
