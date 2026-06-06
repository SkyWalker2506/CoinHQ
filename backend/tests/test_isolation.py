"""Tests for multi-user data isolation (COIN-73)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.keys import _get_owned_profile
from app.api.v1.profiles import delete_profile, get_profile


def _make_user(user_id: int):
    user = MagicMock()
    user.id = user_id
    return user


def _make_profile(profile_id: int, owner_id: int):
    profile = MagicMock()
    profile.id = profile_id
    profile.user_id = owner_id
    return profile


@pytest.mark.asyncio
async def test_get_profile_returns_403_for_wrong_user():
    """Other user's profile must return 403, not 404."""
    from fastapi import HTTPException

    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_profile(profile_id=1, owner_id=99))
    current_user = _make_user(user_id=1)

    with pytest.raises(HTTPException) as exc:
        await get_profile(profile_id=1, db=db, current_user=current_user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_profile_returns_404_for_missing():
    """Non-existent profile must return 404."""
    from fastapi import HTTPException

    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    current_user = _make_user(user_id=1)

    with pytest.raises(HTTPException) as exc:
        await get_profile(profile_id=999, db=db, current_user=current_user)

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_profile_returns_403_for_wrong_user():
    """Deleting another user's profile must return 403."""
    from fastapi import HTTPException

    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_profile(profile_id=1, owner_id=99))
    current_user = _make_user(user_id=1)

    with pytest.raises(HTTPException) as exc:
        await delete_profile(profile_id=1, db=db, current_user=current_user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_owned_profile_returns_403_for_wrong_user():
    """_get_owned_profile helper must return 403 on ownership mismatch."""
    from fastapi import HTTPException

    db = AsyncMock()
    db.get = AsyncMock(return_value=_make_profile(profile_id=5, owner_id=42))
    current_user = _make_user(user_id=1)

    with pytest.raises(HTTPException) as exc:
        await _get_owned_profile(profile_id=5, db=db, current_user=current_user)

    assert exc.value.status_code == 403
