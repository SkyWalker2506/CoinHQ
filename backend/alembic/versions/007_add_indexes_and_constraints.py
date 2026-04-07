"""add missing indexes and unique constraint on exchange_keys

Revision ID: 007
Revises: 006
Create Date: 2026-04-07
"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Index on share_links.profile_id for faster queries
    op.create_index("ix_share_links_profile_id", "share_links", ["profile_id"])

    # Unique constraint: one key per exchange per profile
    op.create_unique_constraint(
        "uq_exchange_keys_profile_exchange",
        "exchange_keys",
        ["profile_id", "exchange"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_exchange_keys_profile_exchange", "exchange_keys", type_="unique")
    op.drop_index("ix_share_links_profile_id", table_name="share_links")
