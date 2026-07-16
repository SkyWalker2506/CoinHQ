"""make share_links timestamp columns timezone-aware

The app writes timezone-aware datetimes (datetime.now(UTC)) to share_links.
The original columns were created as TIMESTAMP WITHOUT TIME ZONE (migrations
002/004), which asyncpg rejects for tz-aware values ("can't subtract
offset-naive and offset-aware datetimes"), breaking the public share view and
view-count update on Postgres. Convert them to TIMESTAMP WITH TIME ZONE.

Revision ID: 011
Revises: 010
Create Date: 2026-07-16
"""
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None

_COLS = ("expires_at", "last_viewed_at", "created_at")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return  # SQLite is tz-agnostic; nothing to alter
    for col in _COLS:
        op.execute(
            f"ALTER TABLE share_links ALTER COLUMN {col} "
            f"TYPE TIMESTAMP WITH TIME ZONE USING {col} AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for col in _COLS:
        op.execute(
            f"ALTER TABLE share_links ALTER COLUMN {col} "
            f"TYPE TIMESTAMP WITHOUT TIME ZONE USING {col} AT TIME ZONE 'UTC'"
        )
