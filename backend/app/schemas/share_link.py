from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, computed_field


class ShareLinkCreate(BaseModel):
    profile_id: int
    show_total_value: bool = True
    show_coin_amounts: bool = False
    show_exchange_names: bool = False
    show_allocation_pct: bool = True
    expires_at: Optional[datetime] = None
    label: Optional[str] = None


class ShareLinkResponse(BaseModel):
    id: int
    token: str
    profile_id: int
    show_total_value: bool
    show_coin_amounts: bool
    show_exchange_names: bool
    show_allocation_pct: bool
    expires_at: Optional[datetime]
    is_active: bool
    label: Optional[str]
    created_at: datetime

    @computed_field
    @property
    def share_url(self) -> str:
        return f"/share/{self.token}"

    model_config = {"from_attributes": True}


# --- Filtered view returned by the public endpoint ---

class SharedAsset(BaseModel):
    asset: str
    amount: Optional[float] = None        # None when show_coin_amounts=False
    usd_value: Optional[float] = None
    allocation_pct: Optional[float] = None  # populated when show_allocation_pct=True


class SharedExchange(BaseModel):
    exchange_name: str   # "Exchange a3f2b1c4" when show_exchange_names=False
    assets: List[SharedAsset]
    total_usd: Optional[float] = None


class SharedPortfolioView(BaseModel):
    total_usd: Optional[float] = None    # None when show_total_value=False
    exchanges: List[SharedExchange]
    show_total_value: bool
    show_coin_amounts: bool
    show_exchange_names: bool
    show_allocation_pct: bool
