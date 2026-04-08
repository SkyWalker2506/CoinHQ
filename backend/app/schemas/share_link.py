from datetime import datetime

from pydantic import BaseModel, computed_field


class ShareLinkCreate(BaseModel):
    profile_id: int
    show_total_value: bool = True
    show_coin_amounts: bool = False
    show_exchange_names: bool = False
    show_allocation_pct: bool = True
    expires_at: datetime | None = None
    label: str | None = None
    allow_follow: bool = True


class ShareLinkResponse(BaseModel):
    id: int
    token: str
    profile_id: int
    show_total_value: bool
    show_coin_amounts: bool
    show_exchange_names: bool
    show_allocation_pct: bool
    expires_at: datetime | None
    is_active: bool
    label: str | None
    created_at: datetime
    allow_follow: bool = True
    view_count: int = 0
    last_viewed_at: datetime | None = None

    @computed_field
    @property
    def share_url(self) -> str:
        return f"/share/{self.token}"

    model_config = {"from_attributes": True}


# --- Filtered view returned by the public endpoint ---

class SharedAsset(BaseModel):
    asset: str
    amount: float | None = None        # None when show_coin_amounts=False
    usd_value: float | None = None
    allocation_pct: float | None = None  # populated when show_allocation_pct=True


class SharedExchange(BaseModel):
    exchange_name: str   # "Exchange a3f2b1c4" when show_exchange_names=False
    assets: list[SharedAsset]
    total_usd: float | None = None


class FollowedPortfolioResponse(BaseModel):
    id: int
    token: str
    label: str | None
    followed_at: datetime
    model_config = {"from_attributes": True}


class SharedPortfolioView(BaseModel):
    token: str = ""
    profile_name: str = ""
    total_usd: float | None = None
    exchanges: list[SharedExchange]
    show_total_value: bool
    show_coin_amounts: bool
    show_exchange_names: bool
    show_allocation_pct: bool
    allow_follow: bool = True
