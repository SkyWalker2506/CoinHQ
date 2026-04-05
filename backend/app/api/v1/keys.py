from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import encrypt
from app.exchanges.factory import get_adapter, SUPPORTED_EXCHANGES
from app.models.exchange_key import ExchangeKey
from app.models.profile import Profile
from app.schemas.exchange_key import ExchangeKeyCreate, ExchangeKeyRead

router = APIRouter(prefix="/profiles/{profile_id}/keys", tags=["keys"])


@router.get("/", response_model=List[ExchangeKeyRead])
async def list_keys(profile_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ExchangeKey).where(ExchangeKey.profile_id == profile_id)
    )
    return result.scalars().all()


@router.post("/", response_model=ExchangeKeyRead, status_code=status.HTTP_201_CREATED)
async def add_key(
    profile_id: int,
    payload: ExchangeKeyCreate,
    db: AsyncSession = Depends(get_db),
):
    # Validate profile exists
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if payload.exchange.lower() not in SUPPORTED_EXCHANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported exchange. Supported: {SUPPORTED_EXCHANGES}",
        )

    # Validate key works before storing
    adapter = get_adapter(payload.exchange, payload.api_key, payload.api_secret)
    if not await adapter.validate_key():
        raise HTTPException(status_code=400, detail="API key validation failed. Check key/secret and permissions.")

    # Encrypt and store — never log plaintext keys
    key = ExchangeKey(
        profile_id=profile_id,
        exchange=payload.exchange.lower(),
        encrypted_key=encrypt(payload.api_key),
        encrypted_secret=encrypt(payload.api_secret),
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    profile_id: int, key_id: int, db: AsyncSession = Depends(get_db)
):
    key = await db.get(ExchangeKey, key_id)
    if not key or key.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.delete(key)
    await db.commit()
