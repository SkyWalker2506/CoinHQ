from datetime import datetime

from pydantic import BaseModel, Field


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^\S.*\S$|^\S$")


class ProfileRead(BaseModel):
    id: int
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProfileList(BaseModel):
    profiles: list[ProfileRead]
