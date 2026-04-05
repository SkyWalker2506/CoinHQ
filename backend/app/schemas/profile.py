from datetime import datetime

from pydantic import BaseModel


class ProfileCreate(BaseModel):
    name: str


class ProfileRead(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileList(BaseModel):
    profiles: list[ProfileRead]
