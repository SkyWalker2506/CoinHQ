from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Coverage = Literal["full", "partial", "none"]


class AssetCostBasis(BaseModel):
    asset: str
    # AVCO average buy price in USD for the position explained by the venue's
    # own stable-quoted fills. None when coverage is "none".
    avg_buy_price: float | None = None
    # Base quantity acquired through qualifying buys, net of fees charged in
    # the base asset, before any sells.
    bought_qty: float = 0.0
    coverage: Coverage = "none"


class ExchangeCostBasis(BaseModel):
    exchange: str
    # False when the venue does not expose trade history through CoinHQ (or
    # the fetch failed); assets is then empty.
    supported: bool
    assets: list[AssetCostBasis] = []


class CostBasisResponse(BaseModel):
    profile_id: int
    computed_at: datetime
    exchanges: list[ExchangeCostBasis]
