from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.exchange_key import ExchangeKey
from app.models.profile import Profile
from app.models.share_link import ShareLink
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User) -> None:
    if user.tier != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    user_count = await db.scalar(select(func.count(User.id)))
    profile_count = await db.scalar(select(func.count(Profile.id)))
    share_count = await db.scalar(
        select(func.count(ShareLink.id)).where(ShareLink.is_active == True)  # noqa: E712
    )

    exchange_dist_rows = await db.execute(
        select(ExchangeKey.exchange, func.count(ExchangeKey.id)).group_by(ExchangeKey.exchange)
    )

    return {
        "users": user_count,
        "profiles": profile_count,
        "active_share_links": share_count,
        "exchanges": {row[0]: row[1] for row in exchange_dist_rows},
    }
