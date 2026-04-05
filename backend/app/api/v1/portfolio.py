from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import get_db
from app.models.exchange_key import ExchangeKey
from app.models.profile import Profile
from app.schemas.portfolio import PortfolioResponse, AggregatePortfolioResponse
from app.services.portfolio_service import get_portfolio, get_aggregate_portfolio

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/profile/{profile_id}", response_model=PortfolioResponse)
@limiter.limit(settings.RATE_LIMIT_PORTFOLIO)
async def portfolio_for_profile(
    request: Request,
    profile_id: int,
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await db.execute(
        select(ExchangeKey).where(ExchangeKey.profile_id == profile_id)
    )
    keys = result.scalars().all()

    return await get_portfolio(profile.id, profile.name, keys)


@router.get("/aggregate", response_model=AggregatePortfolioResponse)
@limiter.limit(settings.RATE_LIMIT_PORTFOLIO)
async def aggregate_portfolio(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).order_by(Profile.name))
    profiles = result.scalars().all()

    profiles_with_keys = []
    for profile in profiles:
        keys_result = await db.execute(
            select(ExchangeKey).where(ExchangeKey.profile_id == profile.id)
        )
        keys = keys_result.scalars().all()
        profiles_with_keys.append((profile, keys))

    return await get_aggregate_portfolio(profiles_with_keys)
