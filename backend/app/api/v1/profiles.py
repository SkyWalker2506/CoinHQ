
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limits import check_profile_limit
from app.core.security import get_current_user
from app.models.profile import Profile
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfileRead

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/", response_model=list[ProfileRead])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id).order_by(Profile.name)
    )
    return result.scalars().all()


@router.post("/", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: ProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile_count = await db.scalar(
        select(func.count(Profile.id)).where(Profile.user_id == current_user.id)
    )
    if not check_profile_limit(current_user, profile_count):
        raise HTTPException(
            status_code=403,
            detail="Free tier limit: 1 profile. Upgrade to Premium for unlimited profiles.",
        )
    existing = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id, Profile.name == payload.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Profile name already exists")
    profile = Profile(name=payload.name, user_id=current_user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileRead)
async def get_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return profile


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    await db.delete(profile)
    await db.commit()
