"""
GET /api/v1/profiles/{profile_id}/pnl

Returns realized P&L and average cost basis per asset, computed from the
filled TradeOrder records stored by CoinHQ using the average-cost (AVCO)
method.

IMPORTANT — partial data:
    These figures reflect ONLY trades executed through CoinHQ.  Holdings
    purchased or sold directly on the exchange (outside CoinHQ) are not
    known, so avg_cost and realized_pnl_usd are partial estimates.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.pnl import ProfilePnLResponse
from app.services.pnl_service import compute_profile_pnl

router = APIRouter(prefix="/profiles", tags=["pnl"])


@router.get(
    "/{profile_id}/pnl",
    response_model=ProfilePnLResponse,
    summary="Realized P&L and average cost basis (CoinHQ trades only)",
    description=(
        "Returns per-asset realized P&L and average cost basis computed from "
        "filled orders recorded by CoinHQ using the average-cost (AVCO) method. "
        "**Partial data**: trades executed directly on the exchange outside "
        "CoinHQ are not captured, so figures may understate true cost basis "
        "and realized gains/losses."
    ),
)
async def get_profile_pnl(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProfilePnLResponse:
    """Owner-scoped P&L endpoint — returns 404 if profile missing, 403 if not owner."""
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return await compute_profile_pnl(profile_id=profile_id, db=db)
