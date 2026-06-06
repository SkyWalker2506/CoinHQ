from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PortfolioSnapshot(Base):
    """Point-in-time record of a profile's total portfolio value in USD.

    Written at most once per hour per profile when the portfolio is fetched.
    Used to power the portfolio history chart on the dashboard.
    """

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    total_usd = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    profile = relationship("Profile")
