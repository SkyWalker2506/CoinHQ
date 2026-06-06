"""add waitlist table

Revision ID: 009
Revises: 008
Create Date: 2026-06-06
"""
import sqlalchemy as sa

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waitlist",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True, server_default="web"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_waitlist_email", "waitlist", ["email"])
    op.create_index("ix_waitlist_email", "waitlist", ["email"])


def downgrade() -> None:
    op.drop_index("ix_waitlist_email", table_name="waitlist")
    op.drop_constraint("uq_waitlist_email", "waitlist", type_="unique")
    op.drop_table("waitlist")
