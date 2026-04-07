
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import encrypt, get_current_user
from app.exchanges.factory import SUPPORTED_EXCHANGES, get_adapter
from app.models.exchange_key import ExchangeKey
from app.models.profile import Profile
from app.models.user import User
from app.schemas.exchange_key import ExchangeKeyCreate, ExchangeKeyRead

router = APIRouter(prefix="/profiles/{profile_id}/keys", tags=["keys"])


async def _get_owned_profile(
    profile_id: int,
    db: AsyncSession,
    current_user: User,
) -> Profile:
    """Return profile if it belongs to current_user, else 404."""
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return profile


@router.get("/", response_model=list[ExchangeKeyRead])
async def list_keys(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_profile(profile_id, db, current_user)
    result = await db.execute(
        select(ExchangeKey).where(ExchangeKey.profile_id == profile_id)
    )
    return result.scalars().all()


@router.post("/", response_model=ExchangeKeyRead, status_code=status.HTTP_201_CREATED)
async def add_key(
    request: Request,
    profile_id: int,
    payload: ExchangeKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_profile(profile_id, db, current_user)

    if payload.exchange.lower() not in SUPPORTED_EXCHANGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported exchange. Supported: {SUPPORTED_EXCHANGES}",
        )

    # Validate key works before storing
    http_client = getattr(request.app.state, "http_client", None)
    adapter = get_adapter(payload.exchange, payload.api_key, payload.api_secret, http_client=http_client)
    try:
        if not await adapter.validate_key():
            raise HTTPException(status_code=400, detail="API key validation failed. Check key/secret and permissions.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Could not reach exchange API. Please try again.")

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
    logger.info("api_key_created", user_id=current_user.id, exchange=payload.exchange.lower(), key_id=key.id)
    return key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    profile_id: int,
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_profile(profile_id, db, current_user)
    key = await db.get(ExchangeKey, key_id)
    if not key or key.profile_id != profile_id:
        raise HTTPException(status_code=404, detail="Key not found")
    await db.delete(key)
    await db.commit()
    logger.info("api_key_deleted", user_id=current_user.id, key_id=key_id, profile_id=profile_id)
