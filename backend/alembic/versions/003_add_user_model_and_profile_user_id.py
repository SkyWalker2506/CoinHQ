"""add user model and profile user_id

Revision ID: 003
Revises: 002
Create Date: 2026-04-05
"""
import sqlalchemy as sa

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("google_id", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Add user_id column to profiles (nullable first for existing rows)
    op.add_column(
        "profiles",
        sa.Column("user_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_profiles_user_id_users",
        "profiles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_profiles_user_id"), "profiles", ["user_id"], unique=False)

    # Remove the old unique constraint on profiles.name if it exists
    op.execute("ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_name_key")


def downgrade() -> None:
    op.create_unique_constraint("profiles_name_key", "profiles", ["name"])
    op.drop_index(op.f("ix_profiles_user_id"), table_name="profiles")
    op.drop_constraint("fk_profiles_user_id_users", "profiles", type_="foreignkey")
    op.drop_column("profiles", "user_id")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")
