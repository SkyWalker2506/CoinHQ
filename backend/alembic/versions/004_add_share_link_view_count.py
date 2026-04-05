"""add share link view count

Revision ID: 004
Revises: 003
Create Date: 2026-04-05
"""
import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "share_links",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "share_links",
        sa.Column("last_viewed_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("share_links", "last_viewed_at")
    op.drop_column("share_links", "view_count")
