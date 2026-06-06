from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class TradeOrder(Base):
    """Audit record for every buy/sell order placed through CoinHQ.

    Used both as an immutable trade log and as the source of truth for the
    per-share-link 24h spend limit. Withdrawals/transfers are never recorded
    here because they are never permitted.
    """

    __tablename__ = "trade_orders"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    # Set when the order was placed by a delegate via a share link; NULL for owner trades.
    share_link_id = Column(Integer, ForeignKey("share_links.id", ondelete="SET NULL"), nullable=True, index=True)

    exchange = Column(String(50), nullable=False)
    symbol = Column(String(30), nullable=False)        # e.g. "BTCUSDT"
    base_asset = Column(String(20), nullable=False)    # e.g. "BTC"
    side = Column(String(10), nullable=False)          # "buy" | "sell"
    usd_value = Column(Float, nullable=False)          # quote amount in USD(T)
    amount = Column(Float, nullable=True)              # filled base quantity (if reported)

    actor = Column(String(20), nullable=False)         # "owner" | "delegate"
    status = Column(String(20), nullable=False, server_default="pending")  # pending|filled|failed
    exchange_order_id = Column(String(64), nullable=True)
    error = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    profile = relationship("Profile")
