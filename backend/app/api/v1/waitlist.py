from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.waitlist import Waitlist
from app.schemas.waitlist import WaitlistCreate, WaitlistOut

router = APIRouter(prefix="/waitlist", tags=["waitlist"])


@router.post("", response_model=WaitlistOut, status_code=status.HTTP_201_CREATED)
async def join_waitlist(
    payload: WaitlistCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add an email to the waitlist. Idempotent: duplicate emails return 200."""
    result = await db.execute(
        select(Waitlist).where(Waitlist.email == payload.email)
    )
    existing = result.scalar_one_or_none()
    if existing:
        out = WaitlistOut.model_validate(existing)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=jsonable_encoder(out),
        )

    entry = Waitlist(
        email=payload.email,
        plan=payload.plan,
        source="web",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
