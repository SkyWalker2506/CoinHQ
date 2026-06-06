"""add user tier

Revision ID: 005
Revises: 004
Create Date: 2026-04-05

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tier", sa.String(length=50), nullable=False, server_default="free"),
    )


def downgrade() -> None:
    op.drop_column("users", "tier")
