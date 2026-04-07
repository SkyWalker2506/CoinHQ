from datetime import datetime

from pydantic import BaseModel, Field


class ExchangeKeyCreate(BaseModel):
    exchange: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=8, max_length=512)
    api_secret: str = Field(..., min_length=8, max_length=1024)


class ExchangeKeyRead(BaseModel):
    id: int
    profile_id: int
    exchange: str
    created_at: datetime

    class Config:
        from_attributes = True
