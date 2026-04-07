from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExchangeKey(Base):
    __tablename__ = "exchange_keys"
    __table_args__ = (
        UniqueConstraint("profile_id", "exchange", name="uq_exchange_keys_profile_exchange"),
    )

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)  # "binance", "bybit", "okx"
    # Fernet-encrypted base64 tokens — never stored as plaintext
    encrypted_key = Column(String(512), nullable=False)
    encrypted_secret = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="exchange_keys")
