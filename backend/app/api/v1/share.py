import hashlib
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.exchange_key import ExchangeKey
from app.models.followed_portfolio import FollowedPortfolio
from app.models.profile import Profile
from app.models.share_link import ShareLink
from app.models.user import User
from app.schemas.share_link import (
    FollowedPortfolioResponse,
    SharedAsset,
    SharedExchange,
    SharedPortfolioView,
    ShareLinkCreate,
    ShareLinkResponse,
)
from app.services.portfolio_service import get_portfolio

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["share"])


# ── Authenticated endpoints ─────────────────────────────────────────────────

@router.post("/share", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_share_link(
    payload: ShareLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.get(Profile, payload.profile_id)
    if not profile or profile.user_id != current_user.id:
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
        allow_follow=payload.allow_follow,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get("/share", response_model=list[ShareLinkResponse])
async def list_share_links(
    profile_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(ShareLink).join(Profile).where(
        ShareLink.is_active == True,  # noqa: E712
        Profile.user_id == current_user.id,
    )
    if profile_id is not None:
        query = query.where(ShareLink.profile_id == profile_id)
    result = await db.execute(query.order_by(ShareLink.created_at.desc()))
    return result.scalars().all()


@router.delete("/share/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_share_link(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = await db.get(ShareLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")

    profile = await db.get(Profile, link.profile_id)
    if not profile or profile.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Share link not found")

    link.is_active = False
    await db.commit()


# ── Follow endpoints ─────────────────────────────────────────────────────────

@router.post("/followed/{token}", response_model=FollowedPortfolioResponse, status_code=status.HTTP_201_CREATED)
async def follow_portfolio(
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a shared portfolio to the current user's followed list."""
    result = await db.execute(
        select(ShareLink).where(ShareLink.token == token, ShareLink.is_active == True)  # noqa: E712
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found or revoked")
    if not link.allow_follow:
        raise HTTPException(status_code=403, detail="This portfolio does not allow following")

    # Idempotent — return existing if already followed
    existing = await db.execute(
        select(FollowedPortfolio).where(
            FollowedPortfolio.user_id == current_user.id,
            FollowedPortfolio.token == token,
        )
    )
    followed = existing.scalar_one_or_none()
    if followed:
        return followed

    followed = FollowedPortfolio(
        user_id=current_user.id,
        token=token,
        label=link.label,
    )
    db.add(followed)
    await db.commit()
    await db.refresh(followed)
    return followed


@router.get("/followed", response_model=list[FollowedPortfolioResponse])
async def list_followed(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FollowedPortfolio)
        .where(FollowedPortfolio.user_id == current_user.id)
        .order_by(FollowedPortfolio.followed_at.desc())
    )
    return result.scalars().all()


@router.delete("/followed/{followed_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_portfolio(
    followed_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    followed = await db.get(FollowedPortfolio, followed_id)
    if not followed or followed.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(followed)
    await db.commit()


# ── Public endpoint (no auth, rate-limited) ─────────────────────────────────

def _mask_exchange(name: str) -> str:
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

    # Check expiry BEFORE incrementing view count
    if link.expires_at is not None:
        now = datetime.now(UTC)
        exp = link.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        if now > exp:
            raise HTTPException(status_code=410, detail="This link has expired")

    # Atomic view count increment (avoids race condition with concurrent requests)
    await db.execute(
        update(ShareLink)
        .where(ShareLink.id == link.id)
        .values(view_count=ShareLink.view_count + 1, last_viewed_at=datetime.now(UTC))
    )
    await db.commit()

    profile = await db.get(Profile, link.profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile no longer exists")

    keys_result = await db.execute(
        select(ExchangeKey).where(ExchangeKey.profile_id == link.profile_id)
    )
    keys = keys_result.scalars().all()

    portfolio = await get_portfolio(link.profile_id, profile.name, keys)

    grand_total = portfolio.total_usd
    filtered_exchanges: list[SharedExchange] = []
    for ex in portfolio.exchanges:
        exchange_label = ex.exchange if link.show_exchange_names else _mask_exchange(ex.exchange)
        assets: list[SharedAsset] = []
        for bal in ex.balances:
            if bal.total == 0:
                continue
            alloc_pct: float | None = None
            if link.show_allocation_pct and grand_total and grand_total > 0:
                alloc_pct = round((bal.usd_value or 0) / grand_total * 100, 2)
            assets.append(SharedAsset(
                asset=bal.asset,
                amount=bal.total if link.show_coin_amounts else None,
                usd_value=bal.usd_value if link.show_total_value else None,
                allocation_pct=alloc_pct,
            ))
        filtered_exchanges.append(SharedExchange(
            exchange_name=exchange_label,
            assets=assets,
            total_usd=ex.total_usd if link.show_total_value else None,
        ))

    return SharedPortfolioView(
        token=token,
        profile_name=profile.name,
        total_usd=portfolio.total_usd if link.show_total_value else None,
        exchanges=filtered_exchanges,
        show_total_value=link.show_total_value,
        show_coin_amounts=link.show_coin_amounts,
        show_exchange_names=link.show_exchange_names,
        show_allocation_pct=link.show_allocation_pct,
        allow_follow=link.allow_follow,
    )
