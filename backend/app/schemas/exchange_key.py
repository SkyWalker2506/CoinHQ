from datetime import datetime

from pydantic import BaseModel


class ExchangeKeyCreate(BaseModel):
    exchange: str  # "binance", "bybit", "okx"
    api_key: str
    api_secret: str


class ExchangeKeyRead(BaseModel):
    id: int
    profile_id: int
    exchange: str
    created_at: datetime

    class Config:
        from_attributes = True
