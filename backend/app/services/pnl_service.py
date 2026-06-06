"""
Realized P&L and average cost-basis service.

Uses the average-cost (AVCO) method applied to filled TradeOrder records in
chronological order.

IMPORTANT — partial data:
    Only orders placed through CoinHQ are visible.  Holdings acquired or sold
    directly on the exchange are unknown, so the computed avg_cost and
    realized_pnl_usd are partial.  Callers and the UI must communicate this
    limitation to end-users.

Edge case — over-sell:
    If a sell order's amount exceeds the qty currently tracked in CoinHQ
    (because some buys happened outside CoinHQ), the sell is clamped to the
    tracked qty.  This prevents negative holdings.  The P&L is computed only
    on the clamped qty; the remainder is silently ignored.
"""

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade_order import TradeOrder
from app.schemas.pnl import AssetPnL, ProfilePnLResponse


@dataclass
class _AssetState:
    """Mutable accumulator for one (profile, base_asset) pair."""

    qty: float = 0.0
    cost_basis_total: float = 0.0  # USD cost of current open position
    realized_pnl: float = 0.0
    total_bought_usd: float = 0.0
    total_sold_usd: float = 0.0
    buy_count: int = 0
    sell_count: int = 0


async def compute_profile_pnl(
    profile_id: int,
    db: AsyncSession,
) -> ProfilePnLResponse:
    """Compute realized P&L and average cost basis for *profile_id*.

    Returns a :class:`ProfilePnLResponse` with one :class:`AssetPnL` entry
    per asset that has at least one filled trade.  Assets are returned sorted
    alphabetically for stable ordering.

    Only ``status == 'filled'`` orders with a non-null ``amount`` are
    processed.  Orders are processed in ``created_at`` ascending order so
    that the AVCO math is deterministic.
    """
    result = await db.execute(
        select(TradeOrder)
        .where(
            TradeOrder.profile_id == profile_id,
            TradeOrder.status == "filled",
            TradeOrder.amount.is_not(None),
        )
        .order_by(TradeOrder.created_at.asc())
    )
    orders = result.scalars().all()

    states: dict[str, _AssetState] = defaultdict(_AssetState)

    for order in orders:
        asset = order.base_asset.upper()
        s = states[asset]
        amount: float = order.amount  # type: ignore[assignment]  # guarded by IS NOT NULL
        usd_value: float = order.usd_value

        if order.side == "buy":
            s.qty += amount
            s.cost_basis_total += usd_value
            s.total_bought_usd += usd_value
            s.buy_count += 1

        elif order.side == "sell":
            # Clamp sell qty to what we track — see module docstring.
            sell_qty = min(amount, s.qty)

            if sell_qty > 0 and s.qty > 0:
                sell_price_per_unit = usd_value / amount
                avg_cost = s.cost_basis_total / s.qty
                s.realized_pnl += sell_qty * (sell_price_per_unit - avg_cost)
                s.cost_basis_total -= sell_qty * avg_cost
                s.qty -= sell_qty

            s.total_sold_usd += usd_value
            s.sell_count += 1

    asset_pnls: list[AssetPnL] = []
    for asset, s in sorted(states.items()):
        avg_cost: float | None = (
            s.cost_basis_total / s.qty if s.qty > 1e-12 else None
        )
        asset_pnls.append(
            AssetPnL(
                base_asset=asset,
                current_qty=s.qty,
                avg_cost=avg_cost,
                realized_pnl_usd=s.realized_pnl,
                total_bought_usd=s.total_bought_usd,
                total_sold_usd=s.total_sold_usd,
                buy_count=s.buy_count,
                sell_count=s.sell_count,
            )
        )

    total_realized = sum(a.realized_pnl_usd for a in asset_pnls)
    return ProfilePnLResponse(
        assets=asset_pnls,
        total_realized_pnl_usd=total_realized,
    )
