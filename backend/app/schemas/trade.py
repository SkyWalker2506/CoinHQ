from datetime import datetime

from pydantic import BaseModel, Field


class TradeOrderRequest(BaseModel):
    exchange: str = Field(..., min_length=1, max_length=50)
    asset: str = Field(..., min_length=1, max_length=20)  # base asset, e.g. "BTC"
    side: str = Field(..., pattern="^(buy|sell)$")
    usd_amount: float = Field(..., gt=0, description="Quote amount in USD(T) to spend/sell")


class TradeOrderResponse(BaseModel):
    id: int
    exchange: str
    symbol: str
    base_asset: str
    side: str
    usd_value: float
    amount: float | None = None
    status: str
    actor: str
    exchange_order_id: str | None = None
    error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
