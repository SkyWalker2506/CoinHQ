import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models.share_link import ShareLink
from app.models.exchange_key import ExchangeKey
from app.models.profile import Profile
from app.schemas.share_link import (
    ShareLinkCreate,
    ShareLinkResponse,
    SharedPortfolioView,
    SharedExchange,
    SharedAsset,
)
from app.services.portfolio_service import get_portfolio

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["share"])


# ── Authenticated endpoints ─────────────────────────────────────────────────

@router.post("/share", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_share_link(
    payload: ShareLinkCreate,
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(Profile, payload.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    link = ShareLink(
        profile_id=payload.profile_id,
        token=ShareLink.generate_token(),
        show_total_value=payload.show_total_value,
        show_coin_amounts=payload.show_coin_amounts,
        show_exchange_names=payload.show_exchange_names,
        show_allocation_pct=payload.show_allocation_pct,
        expires_at=payload.expires_at,
        label=payload.label,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get("/share", response_model=List[ShareLinkResponse])
async def list_share_links(
    profile_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ShareLink).where(ShareLink.is_active == True)  # noqa: E712
    if profile_id is not None:
        query = query.where(ShareLink.profile_id == profile_id)
    result = await db.execute(query.order_by(ShareLink.created_at.desc()))
    return result.scalars().all()


@router.delete("/share/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
):
    link = await db.get(ShareLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")
    link.is_active = False
    await db.commit()


# ── Public endpoint (no auth, rate-limited) ─────────────────────────────────

def _mask_exchange(name: str) -> str:
    """Return a stable but irreversible alias for an exchange name."""
    digest = hashlib.sha256(name.encode()).hexdigest()[:8]
    return f"Exchange {digest}"


@router.get("/public/share/{token}", response_model=SharedPortfolioView)
@limiter.limit("30/minute")
async def public_share_view(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShareLink).where(ShareLink.token == token, ShareLink.is_active == True)  # noqa: E712
    )
    link = result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=404, detail="Link not found or has been revoked")

    if link.expires_at is not None:
        now = datetime.now(timezone.utc)
        exp = link.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            raise HTTPException(status_code=410, detail="This link has expired")

    # Fetch portfolio data
    keys_result = await db.execute(
        select(ExchangeKey).where(ExchangeKey.profile_id == link.profile_id)
    )
    keys = keys_result.scalars().all()

    profile = await db.get(Profile, link.profile_id)
    portfolio = await get_portfolio(link.profile_id, profile.name if profile else "", keys)

    # Build filtered view
    grand_total = portfolio.total_usd

    filtered_exchanges: List[SharedExchange] = []
    for ex in portfolio.exchanges:
        exchange_label = ex.exchange if link.show_exchange_names else _mask_exchange(ex.exchange)

        assets: List[SharedAsset] = []
        for bal in ex.balances:
            if bal.total == 0:
                continue
            alloc_pct: Optional[float] = None
            if link.show_allocation_pct and grand_total and grand_total > 0:
                alloc_pct = round((bal.usd_value or 0) / grand_total * 100, 2)

            assets.append(SharedAsset(
                asset=bal.asset,
                amount=bal.total if link.show_coin_amounts else None,
                usd_value=bal.usd_value,
                allocation_pct=alloc_pct,
            ))

        filtered_exchanges.append(SharedExchange(
            exchange_name=exchange_label,
            assets=assets,
            total_usd=ex.total_usd,
        ))

    return SharedPortfolioView(
        total_usd=portfolio.total_usd if link.show_total_value else None,
        exchanges=filtered_exchanges,
        show_total_value=link.show_total_value,
        show_coin_amounts=link.show_coin_amounts,
        show_exchange_names=link.show_exchange_names,
        show_allocation_pct=link.show_allocation_pct,
    )
