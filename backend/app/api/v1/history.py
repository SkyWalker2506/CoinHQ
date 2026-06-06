"""Portfolio history endpoint — GET /profiles/{profile_id}/history."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.profile import Profile
from app.models.user import User
from app.schemas.portfolio import PortfolioHistoryPoint

router = APIRouter(prefix="/profiles/{profile_id}/history", tags=["history"])

_MAX_DAYS = 365


async def _get_owned_profile(
    profile_id: int,
    db: AsyncSession,
    current_user: User,
) -> Profile:
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return profile


@router.get("/", response_model=list[PortfolioHistoryPoint])
async def portfolio_history(
    profile_id: int,
    days: int = Query(default=30, ge=1, le=_MAX_DAYS),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PortfolioHistoryPoint]:
    """Return portfolio value snapshots for the last N days, oldest→newest."""
    await _get_owned_profile(profile_id, db, current_user)

    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await db.execute(
        select(PortfolioSnapshot)
        .where(
            PortfolioSnapshot.profile_id == profile_id,
            PortfolioSnapshot.created_at >= cutoff,
        )
        .order_by(PortfolioSnapshot.created_at.asc())
    )
    snapshots = result.scalars().all()
    return [PortfolioHistoryPoint.model_validate(s) for s in snapshots]
