"""
Pydantic schemas for the realized P&L / average cost basis endpoint.

IMPORTANT SEMANTIC NOTE — partial data:
    All figures here reflect ONLY trades executed THROUGH CoinHQ.
    Holdings bought or sold directly on the exchange (outside CoinHQ) are
    invisible to this calculation, so avg_cost and realized_pnl_usd are
    partial estimates. The UI must make this limitation clear to the user.
"""

from pydantic import BaseModel, ConfigDict, Field


class AssetPnL(BaseModel):
    """Realized P&L and cost-basis summary for a single base asset.

    Computed using the average-cost (AVCO) method over all filled CoinHQ
    orders, processed in chronological order.  Figures are partial — see
    module docstring.
    """

    model_config = ConfigDict(from_attributes=True)

    base_asset: str = Field(
        description="The base asset ticker, e.g. 'BTC'.",
    )
    current_qty: float = Field(
        description=(
            "Net quantity still held according to CoinHQ trade history "
            "(buys minus sells, clamped to ≥0)."
        ),
    )
    avg_cost: float | None = Field(
        default=None,
        description=(
            "Average cost per unit in USD for the current open position. "
            "Null when current_qty is zero (no open position)."
        ),
    )
    realized_pnl_usd: float = Field(
        description=(
            "Total realized profit/loss in USD from completed sells recorded "
            "in CoinHQ.  Positive = profit, negative = loss.  Partial — see "
            "module docstring."
        ),
    )
    total_bought_usd: float = Field(
        description="Sum of usd_value across all filled buy orders for this asset.",
    )
    total_sold_usd: float = Field(
        description="Sum of usd_value across all filled sell orders for this asset.",
    )
    buy_count: int = Field(description="Number of filled buy orders included.")
    sell_count: int = Field(description="Number of filled sell orders included.")


class ProfilePnLResponse(BaseModel):
    """Response for GET /api/v1/profiles/{profile_id}/pnl.

    IMPORTANT: figures reflect ONLY trades executed through CoinHQ.
    Holdings purchased or sold directly on the exchange are not captured.
    """

    assets: list[AssetPnL] = Field(
        description="Per-asset P&L breakdown, one entry per traded asset.",
    )
    total_realized_pnl_usd: float = Field(
        description="Sum of realized_pnl_usd across all assets.",
    )
