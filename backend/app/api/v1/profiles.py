from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.profile import Profile
from app.schemas.profile import ProfileCreate, ProfileRead

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/", response_model=List[ProfileRead])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile).order_by(Profile.name))
    return result.scalars().all()


@router.post("/", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(payload: ProfileCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Profile).where(Profile.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Profile name already exists")
    profile = Profile(name=payload.name)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileRead)
async def get_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(profile_id: int, db: AsyncSession = Depends(get_db)):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(profile)
    await db.commit()
