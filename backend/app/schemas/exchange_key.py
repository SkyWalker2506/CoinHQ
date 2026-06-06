from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ExchangeKeyCreate(BaseModel):
    exchange: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=8, max_length=512)
    api_secret: str = Field(..., min_length=8, max_length=1024)
    # "read_only" rejects any write permission; "trade" allows spot orders but
    # still rejects withdrawal/transfer permissions.
    key_type: Literal["read_only", "trade"] = "read_only"


class ExchangeKeyRead(BaseModel):
    id: int
    profile_id: int
    exchange: str
    key_type: str = "read_only"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
