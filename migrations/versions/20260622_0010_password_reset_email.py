"""add password reset fields

Revision ID: 20260622_0010
Revises: 20260622_0009
Create Date: 2026-06-22 23:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260622_0010"
down_revision: Union[str, None] = "20260622_0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("password_reset_token_hash", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("password_reset_expires_at")
        batch_op.drop_column("password_reset_token_hash")
