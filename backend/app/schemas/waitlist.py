import re
from datetime import datetime

from pydantic import BaseModel, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class WaitlistCreate(BaseModel):
    email: str
    plan: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        v = str(v).strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email address")
        return v


class WaitlistOut(BaseModel):
    id: int
    email: str
    plan: str | None
    source: str | None
    created_at: datetime

    class Config:
        from_attributes = True
