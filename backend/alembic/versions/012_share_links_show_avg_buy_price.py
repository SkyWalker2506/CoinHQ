"""add share_links.show_avg_buy_price

Opt-in flag: the public share view only fetches exchange trade history (to
show the average buy price per coin) for links that turned it on.

Revision ID: 012
Revises: 011
Create Date: 2026-09-27
"""
import sqlalchemy as sa

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "share_links",
        sa.Column(
            "show_avg_buy_price", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("share_links", "show_avg_buy_price")
