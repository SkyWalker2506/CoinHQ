"""add follow feature — allow_follow on share_links + followed_portfolios table

Revision ID: 006
Revises: 005
Create Date: 2026-04-06
"""
import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add allow_follow flag to share_links
    op.add_column("share_links", sa.Column("allow_follow", sa.Boolean(), nullable=False, server_default="true"))

    # followed_portfolios: user → share_link token
    op.create_table(
        "followed_portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("followed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "token", name="uq_followed_user_token"),
    )
    op.create_index("ix_followed_portfolios_user_id", "followed_portfolios", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_followed_portfolios_user_id", table_name="followed_portfolios")
    op.drop_table("followed_portfolios")
    op.drop_column("share_links", "allow_follow")
