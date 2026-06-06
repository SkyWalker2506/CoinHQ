from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.profile import Profile
from app.models.trade_order import TradeOrder
from app.models.user import User
from app.schemas.trade import TradeOrderRequest, TradeOrderResponse
from app.services.trade_service import execute_trade

router = APIRouter(prefix="/profiles/{profile_id}/trade", tags=["trade"])


async def _get_owned_profile(profile_id: int, db: AsyncSession, current_user: User) -> Profile:
    profile = await db.get(Profile, profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("", response_model=TradeOrderResponse)
async def owner_trade(
    request: Request,
    profile_id: int,
    payload: TradeOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Place a spot buy/sell order on one of your own profiles using its trade key."""
    profile = await _get_owned_profile(profile_id, db, current_user)
    http_client = getattr(request.app.state, "http_client", None)
    return await execute_trade(
        db,
        profile=profile,
        exchange=payload.exchange,
        side=payload.side,
        base_asset=payload.asset,
        usd_amount=payload.usd_amount,
        actor="owner",
        http_client=http_client,
    )


@router.get("", response_model=list[TradeOrderResponse])
async def list_trades(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the most recent trade orders for a profile (owner + delegate)."""
    await _get_owned_profile(profile_id, db, current_user)
    result = await db.execute(
        select(TradeOrder)
        .where(TradeOrder.profile_id == profile_id)
        .order_by(TradeOrder.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()
