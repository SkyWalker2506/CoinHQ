"""Tests for api/v1/share.py — share links, public view, and follow."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.share import (
    _mask_exchange,
    create_share_link,
    follow_portfolio,
    revoke_share_link,
    unfollow_portfolio,
)


def _make_user(user_id: int = 1):
    user = MagicMock()
    user.id = user_id
    return user


def _make_profile(profile_id: int = 1, owner_id: int = 1):
    profile = MagicMock()
    profile.id = profile_id
    profile.user_id = owner_id
    return profile


def _make_share_link(
    link_id: int = 1,
    profile_id: int = 1,
    token: str = "abc123",
    is_active: bool = True,
    allow_follow: bool = True,
    expires_at=None,
    show_total_value: bool = True,
    show_coin_amounts: bool = True,
    show_exchange_names: bool = True,
    show_allocation_pct: bool = True,
):
    link = MagicMock()
    link.id = link_id
    link.profile_id = profile_id
    link.token = token
    link.is_active = is_active
    link.allow_follow = allow_follow
    link.expires_at = expires_at
    link.show_total_value = show_total_value
    link.show_coin_amounts = show_coin_amounts
    link.show_exchange_names = show_exchange_names
    link.show_allocation_pct = show_allocation_pct
    link.view_count = 0
    link.label = "test"
    return link


# ── _mask_exchange ────────────────────────────────────────────────────────────

class TestMaskExchange:
    def test_masks_exchange_name(self):
        result = _mask_exchange("binance")
        assert result.startswith("Exchange ")
        assert "binance" not in result

    def test_same_name_produces_same_mask(self):
        assert _mask_exchange("bybit") == _mask_exchange("bybit")

    def test_different_names_produce_different_masks(self):
        assert _mask_exchange("binance") != _mask_exchange("bybit")


# ── create_share_link ─────────────────────────────────────────────────────────

class TestCreateShareLink:
    @pytest.mark.asyncio
    async def test_rejects_non_owned_profile(self):
        db = AsyncMock()
        # Profile belongs to user 99, not current user 1
        db.get = AsyncMock(return_value=_make_profile(profile_id=5, owner_id=99))

        payload = MagicMock()
        payload.profile_id = 5

        with pytest.raises(HTTPException) as exc:
            await create_share_link(
                payload=payload,
                db=db,
                current_user=_make_user(1),
            )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_missing_profile(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        payload = MagicMock()
        payload.profile_id = 999

        with pytest.raises(HTTPException) as exc:
            await create_share_link(
                payload=payload,
                db=db,
                current_user=_make_user(1),
            )
        assert exc.value.status_code == 404


# ── revoke_share_link ─────────────────────────────────────────────────────────

class TestRevokeShareLink:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_link(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await revoke_share_link(link_id=999, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_for_non_owned_link(self):
        link = _make_share_link(link_id=1, profile_id=5)
        profile = _make_profile(profile_id=5, owner_id=99)

        db = AsyncMock()
        db.get = AsyncMock(side_effect=[link, profile])

        with pytest.raises(HTTPException) as exc:
            await revoke_share_link(link_id=1, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sets_is_active_false(self):
        link = _make_share_link(link_id=1, profile_id=5)
        profile = _make_profile(profile_id=5, owner_id=1)

        db = AsyncMock()
        db.get = AsyncMock(side_effect=[link, profile])
        db.commit = AsyncMock()

        await revoke_share_link(link_id=1, db=db, current_user=_make_user(1))
        assert link.is_active is False


# ── follow_portfolio ──────────────────────────────────────────────────────────

class TestFollowPortfolio:
    @pytest.mark.asyncio
    async def test_rejects_revoked_link(self):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await follow_portfolio(token="bad-token", db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_when_follow_not_allowed(self):
        link = _make_share_link(allow_follow=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = link

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc:
            await follow_portfolio(token="abc123", db=db, current_user=_make_user(1))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_idempotent_returns_existing(self):
        link = _make_share_link(allow_follow=True)
        existing_follow = MagicMock()
        existing_follow.id = 10

        mock_link_result = MagicMock()
        mock_link_result.scalar_one_or_none.return_value = link

        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = existing_follow

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[mock_link_result, mock_existing_result])

        result = await follow_portfolio(token="abc123", db=db, current_user=_make_user(1))
        assert result.id == 10


# ── unfollow_portfolio ────────────────────────────────────────────────────────

class TestUnfollowPortfolio:
    @pytest.mark.asyncio
    async def test_returns_404_for_missing_follow(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await unfollow_portfolio(followed_id=999, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_for_other_users_follow(self):
        follow = MagicMock()
        follow.user_id = 99  # not current user

        db = AsyncMock()
        db.get = AsyncMock(return_value=follow)

        with pytest.raises(HTTPException) as exc:
            await unfollow_portfolio(followed_id=1, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_deletes_own_follow(self):
        follow = MagicMock()
        follow.user_id = 1

        db = AsyncMock()
        db.get = AsyncMock(return_value=follow)
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        await unfollow_portfolio(followed_id=1, db=db, current_user=_make_user(1))
        db.delete.assert_called_once_with(follow)
