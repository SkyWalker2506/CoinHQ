
from pydantic import BaseModel


class Balance(BaseModel):
    asset: str
    free: float
    locked: float
    total: float
    usd_value: float | None = None


class ExchangeBalance(BaseModel):
    exchange: str
    balances: list[Balance]
    total_usd: float


class PortfolioResponse(BaseModel):
    profile_id: int
    profile_name: str
    exchanges: list[ExchangeBalance]
    total_usd: float
    cached: bool = False


class ProfilePortfolio(BaseModel):
    profile_id: int
    profile_name: str
    total_usd: float
    exchanges: list[ExchangeBalance]


class AggregatePortfolioResponse(BaseModel):
    profiles: list[ProfilePortfolio]
    grand_total_usd: float
    asset_totals: dict[str, float]  # asset -> total USD across all profiles
