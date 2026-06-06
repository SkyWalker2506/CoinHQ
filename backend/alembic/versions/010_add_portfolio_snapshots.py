"""add portfolio_snapshots table

Revision ID: 010
Revises: 009
Create Date: 2026-06-06
"""
import sqlalchemy as sa

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("total_usd", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_portfolio_snapshots_profile_id", "portfolio_snapshots", ["profile_id"])
    op.create_index("ix_portfolio_snapshots_profile_id_created_at", "portfolio_snapshots", ["profile_id", "created_at"])
    op.create_index("ix_portfolio_snapshots_created_at", "portfolio_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_snapshots_created_at", table_name="portfolio_snapshots")
    op.drop_index("ix_portfolio_snapshots_profile_id_created_at", table_name="portfolio_snapshots")
    op.drop_index("ix_portfolio_snapshots_profile_id", table_name="portfolio_snapshots")
    op.drop_table("portfolio_snapshots")
