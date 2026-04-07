
from enum import StrEnum

from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserTier(StrEnum):
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    google_id = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tier = Column(String(50), nullable=False, default="free")

    profiles = relationship("Profile", back_populates="user", cascade="all, delete-orphan")
