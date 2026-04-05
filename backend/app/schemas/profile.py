from pydantic import BaseModel
from datetime import datetime
from typing import List


class ProfileCreate(BaseModel):
    name: str


class ProfileRead(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileList(BaseModel):
    profiles: List[ProfileRead]
