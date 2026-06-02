"""Trade execution service — shared by owner trades and delegated (share-link) trades.

Resolves the profile's encrypted *trade* key, enforces delegate limits, places a
spot market order through the exchange adapter, and records an immutable
TradeOrder. Withdrawals/transfers are never possible: trade keys are validated to
have withdrawals disabled, and adapters only ever place buy/sell orders.
"""

from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import decrypt
from app.core.trade_limits import TradeNotAllowedError, check_delegate_trade
from app.exchanges.factory import get_adapter
from app.models.exchange_key import ExchangeKey
from app.models.profile import Profile
from app.models.share_link import ShareLink
from app.models.trade_order import TradeOrder


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def spent_today_usd(db: AsyncSession, share_link_id: int) -> float:
    """Total USD value of filled delegate orders for a share link in the last 24h."""
    since = datetime.now(UTC) - timedelta(hours=24)
    result = await db.execute(
        select(func.coalesce(func.sum(TradeOrder.usd_value), 0.0)).where(
            TradeOrder.share_link_id == share_link_id,
            TradeOrder.status == "filled",
            TradeOrder.created_at >= since,
        )
    )
    return float(result.scalar() or 0.0)


async def execute_trade(
    db: AsyncSession,
    *,
    profile: Profile,
    exchange: str,
    side: str,
    base_asset: str,
    usd_amount: float,
    actor: str,
    share_link: ShareLink | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> TradeOrder:
    exchange = exchange.lower()
    side = side.lower()
    base_asset = base_asset.upper()

    if usd_amount is None or usd_amount <= 0:
        raise HTTPException(status_code=400, detail="usd_amount must be positive.")
    if side not in ("buy", "sell"):
        raise HTTPException(status_code=400, detail="side must be 'buy' or 'sell'.")

    # Resolve the profile's TRADE key for this exchange.
    result = await db.execute(
        select(ExchangeKey).where(
            ExchangeKey.profile_id == profile.id,
            ExchangeKey.exchange == exchange,
            ExchangeKey.key_type == "trade",
        )
    )
    key = result.scalar_one_or_none()
    if key is None:
        raise HTTPException(
            status_code=400,
            detail=f"No trade key configured for {exchange} on this profile.",
        )

    # Enforce delegate limits (owner trades are not limit-checked).
    if share_link is not None:
        spent = await spent_today_usd(db, share_link.id)
        try:
            check_delegate_trade(
                share_link,
                side=side,
                base_asset=base_asset,
                usd_value=usd_amount,
                spent_today_usd=spent,
            )
        except TradeNotAllowedError as e:
            raise HTTPException(status_code=403, detail=str(e))

    adapter = get_adapter(
        exchange,
        decrypt(key.encrypted_key),
        decrypt(key.encrypted_secret),
        http_client=http_client,
    )

    order = TradeOrder(
        profile_id=profile.id,
        share_link_id=share_link.id if share_link is not None else None,
        exchange=exchange,
        symbol=f"{base_asset}USDT",
        base_asset=base_asset,
        side=side,
        usd_value=usd_amount,
        actor=actor,
        status="pending",
    )

    try:
        resp = await adapter.place_order(base_asset, side, usd_amount)
    except NotImplementedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPError:
        order.status = "failed"
        order.error = "Exchange API error"
        db.add(order)
        await db.commit()
        raise HTTPException(status_code=502, detail="Could not reach exchange API. Order not placed.")

    order.status = "filled"
    order.exchange_order_id = str(resp.get("orderId") or resp.get("ordId") or "") or None
    order.amount = _safe_float(resp.get("executedQty"))
    db.add(order)
    await db.commit()
    await db.refresh(order)
    logger.info(
        "trade_executed",
        profile_id=profile.id,
        exchange=exchange,
        side=side,
        asset=base_asset,
        usd=usd_amount,
        actor=actor,
    )
    return order
