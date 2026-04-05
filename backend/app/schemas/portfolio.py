from pydantic import BaseModel
from typing import List, Optional, Dict


class Balance(BaseModel):
    asset: str
    free: float
    locked: float
    total: float
    usd_value: Optional[float] = None


class ExchangeBalance(BaseModel):
    exchange: str
    balances: List[Balance]
    total_usd: float


class PortfolioResponse(BaseModel):
    profile_id: int
    profile_name: str
    exchanges: List[ExchangeBalance]
    total_usd: float
    cached: bool = False


class ProfilePortfolio(BaseModel):
    profile_id: int
    profile_name: str
    total_usd: float
    exchanges: List[ExchangeBalance]


class AggregatePortfolioResponse(BaseModel):
    profiles: List[ProfilePortfolio]
    grand_total_usd: float
    asset_totals: Dict[str, float]  # asset -> total USD across all profiles
