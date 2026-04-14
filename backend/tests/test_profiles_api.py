"""Tests for api/v1/profiles.py — profile CRUD with tier limits."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.profiles import create_profile, delete_profile, get_profile


def _make_user(user_id: int = 1, tier: str = "free"):
    user = MagicMock()
    user.id = user_id
    user.tier = tier
    return user


def _make_profile(profile_id: int = 1, owner_id: int = 1, name: str = "test"):
    profile = MagicMock()
    profile.id = profile_id
    profile.user_id = owner_id
    profile.name = name
    return profile


class TestGetProfile:
    @pytest.mark.asyncio
    async def test_returns_owned_profile(self):
        profile = _make_profile(profile_id=1, owner_id=1)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        result = await get_profile(profile_id=1, db=db, current_user=_make_user(1))
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await get_profile(profile_id=999, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_wrong_user(self):
        profile = _make_profile(profile_id=1, owner_id=99)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        with pytest.raises(HTTPException) as exc:
            await get_profile(profile_id=1, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 403


class TestDeleteProfile:
    @pytest.mark.asyncio
    async def test_deletes_own_profile(self):
        profile = _make_profile(profile_id=1, owner_id=1)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        await delete_profile(profile_id=1, db=db, current_user=_make_user(1))
        db.delete.assert_called_once_with(profile)

    @pytest.mark.asyncio
    async def test_returns_404_for_missing(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await delete_profile(profile_id=999, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_wrong_user(self):
        profile = _make_profile(profile_id=1, owner_id=99)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        with pytest.raises(HTTPException) as exc:
            await delete_profile(profile_id=1, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 403


class TestCreateProfile:
    @pytest.mark.asyncio
    async def test_free_tier_rejects_at_limit(self):
        db = AsyncMock()
        db.scalar = AsyncMock(return_value=1)  # already has 1 profile

        payload = MagicMock()
        payload.name = "New Profile"

        with pytest.raises(HTTPException) as exc:
            await create_profile(
                payload=payload,
                db=db,
                current_user=_make_user(1, tier="free"),
            )
        assert exc.value.status_code == 403
        assert "Free tier" in exc.value.detail

    @pytest.mark.asyncio
    async def test_rejects_duplicate_name(self):
        existing = _make_profile(name="MyPortfolio")

        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar_one_or_none.return_value = existing

        db = AsyncMock()
        db.scalar = AsyncMock(return_value=0)
        db.execute = AsyncMock(return_value=mock_scalar_result)

        payload = MagicMock()
        payload.name = "MyPortfolio"

        with pytest.raises(HTTPException) as exc:
            await create_profile(
                payload=payload,
                db=db,
                current_user=_make_user(1, tier="premium"),
            )
        assert exc.value.status_code == 400
        assert "already exists" in exc.value.detail
