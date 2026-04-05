from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FollowedPortfolio(Base):
    __tablename__ = "followed_portfolios"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(64))
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    followed_at: Mapped[datetime] = mapped_column(default=func.now())

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uq_followed_user_token"),
    )
