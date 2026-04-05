import secrets
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ShareLink(Base):
    __tablename__ = "share_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"))
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Permission flags
    show_total_value: Mapped[bool] = mapped_column(Boolean, default=True)
    show_coin_amounts: Mapped[bool] = mapped_column(Boolean, default=False)
    show_exchange_names: Mapped[bool] = mapped_column(Boolean, default=False)
    show_allocation_pct: Mapped[bool] = mapped_column(Boolean, default=True)

    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    view_count: Mapped[int] = mapped_column(default=0)
    last_viewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    allow_follow: Mapped[bool] = mapped_column(Boolean, default=True)

    profile = relationship("Profile")

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)
