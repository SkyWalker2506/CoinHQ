"""add trade support: key_type, share-link trade permissions, trade_orders

Revision ID: 008
Revises: 007
Create Date: 2026-06-02
"""
import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # exchange_keys: distinguish read-only vs trade keys, allow both per exchange
    op.add_column(
        "exchange_keys",
        sa.Column("key_type", sa.String(length=20), nullable=False, server_default="read_only"),
    )
    op.drop_constraint("uq_exchange_keys_profile_exchange", "exchange_keys", type_="unique")
    op.create_unique_constraint(
        "uq_exchange_keys_profile_exchange_type",
        "exchange_keys",
        ["profile_id", "exchange", "key_type"],
    )

    # share_links: delegated trade permissions (withdrawals never granted)
    op.add_column(
        "share_links",
        sa.Column("can_trade", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "share_links",
        sa.Column("trade_direction", sa.String(length=10), nullable=False, server_default="both"),
    )
    op.add_column("share_links", sa.Column("trade_allowed_coins", sa.String(length=255), nullable=True))
    op.add_column("share_links", sa.Column("trade_max_per_order_usd", sa.Float(), nullable=True))
    op.add_column("share_links", sa.Column("trade_daily_limit_usd", sa.Float(), nullable=True))

    # trade_orders: immutable audit log + source of truth for the 24h spend limit
    op.create_table(
        "trade_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "profile_id",
            sa.Integer(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "share_link_id",
            sa.Integer(),
            sa.ForeignKey("share_links.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("exchange", sa.String(length=50), nullable=False),
        sa.Column("symbol", sa.String(length=30), nullable=False),
        sa.Column("base_asset", sa.String(length=20), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("usd_value", sa.Float(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("actor", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("exchange_order_id", sa.String(length=64), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trade_orders_profile_id", "trade_orders", ["profile_id"])
    op.create_index("ix_trade_orders_share_link_id", "trade_orders", ["share_link_id"])
    op.create_index("ix_trade_orders_created_at", "trade_orders", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_trade_orders_created_at", table_name="trade_orders")
    op.drop_index("ix_trade_orders_share_link_id", table_name="trade_orders")
    op.drop_index("ix_trade_orders_profile_id", table_name="trade_orders")
    op.drop_table("trade_orders")

    op.drop_column("share_links", "trade_daily_limit_usd")
    op.drop_column("share_links", "trade_max_per_order_usd")
    op.drop_column("share_links", "trade_allowed_coins")
    op.drop_column("share_links", "trade_direction")
    op.drop_column("share_links", "can_trade")

    op.drop_constraint("uq_exchange_keys_profile_exchange_type", "exchange_keys", type_="unique")
    op.create_unique_constraint(
        "uq_exchange_keys_profile_exchange",
        "exchange_keys",
        ["profile_id", "exchange"],
    )
    op.drop_column("exchange_keys", "key_type")
