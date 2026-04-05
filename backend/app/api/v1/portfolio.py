from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.exchange_key import ExchangeKey
from app.models.profile import Profile
from app.models.user import User
from app.schemas.portfolio import AggregatePortfolioResponse, PortfolioResponse
from app.services.portfolio_service import get_aggregate_portfolio, get_portfolio

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/profile/{profile_id}", response_model=PortfolioResponse)
@limiter.limit(settings.RATE_LIMIT_PORTFOLIO)
async def portfolio_for_profile(
    request: Request,
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.get(Profile, profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Profile not found")

    result = await db.execute(
        select(ExchangeKey).where(ExchangeKey.profile_id == profile_id)
    )
    keys = result.scalars().all()

    return await get_portfolio(
        profile.id,
        profile.name,
        keys,
        redis=request.app.state.redis,
        http_client=request.app.state.http_client,
    )


@router.get("/aggregate", response_model=AggregatePortfolioResponse)
@limiter.limit(settings.RATE_LIMIT_PORTFOLIO)
async def aggregate_portfolio(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id).order_by(Profile.name)
    )
    profiles = result.scalars().all()

    profiles_with_keys = []
    for profile in profiles:
        keys_result = await db.execute(
            select(ExchangeKey).where(ExchangeKey.profile_id == profile.id)
        )
        keys = keys_result.scalars().all()
        profiles_with_keys.append((profile, keys))

    return await get_aggregate_portfolio(
        profiles_with_keys,
        redis=request.app.state.redis,
        http_client=request.app.state.http_client,
    )
