"""Tests for api/v1/keys.py — exchange API key management."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.keys import _get_owned_profile, add_key, delete_key


def _make_user(user_id: int = 1):
    user = MagicMock()
    user.id = user_id
    return user


def _make_profile(profile_id: int = 1, owner_id: int = 1):
    profile = MagicMock()
    profile.id = profile_id
    profile.user_id = owner_id
    return profile


class TestGetOwnedProfile:
    @pytest.mark.asyncio
    async def test_returns_profile_for_owner(self):
        profile = _make_profile(profile_id=1, owner_id=5)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        result = await _get_owned_profile(profile_id=1, db=db, current_user=_make_user(5))
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_profile(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await _get_owned_profile(profile_id=999, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_wrong_owner(self):
        profile = _make_profile(profile_id=1, owner_id=99)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        with pytest.raises(HTTPException) as exc:
            await _get_owned_profile(profile_id=1, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 403


class TestAddKey:
    @pytest.mark.asyncio
    async def test_rejects_unsupported_exchange(self):
        db = AsyncMock()
        profile = _make_profile(profile_id=1, owner_id=1)
        db.get = AsyncMock(return_value=profile)

        payload = MagicMock()
        payload.exchange = "unsupported_exchange"
        payload.api_key = "test_key_12345678"
        payload.api_secret = "test_secret_12345678"

        request = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await add_key(
                request=request,
                profile_id=1,
                payload=payload,
                db=db,
                current_user=_make_user(1),
            )
        assert exc.value.status_code == 400
        assert "Unsupported exchange" in exc.value.detail

    @pytest.mark.asyncio
    async def test_rejects_key_that_fails_validation(self):
        db = AsyncMock()
        profile = _make_profile(profile_id=1, owner_id=1)
        db.get = AsyncMock(return_value=profile)

        payload = MagicMock()
        payload.exchange = "binance"
        payload.api_key = "test_key_12345678"
        payload.api_secret = "test_secret_12345678"

        request = MagicMock()
        request.app.state.http_client = None

        mock_adapter = AsyncMock()
        mock_adapter.validate_key = AsyncMock(return_value=False)

        with patch("app.api.v1.keys.get_adapter", return_value=mock_adapter):
            with pytest.raises(HTTPException) as exc:
                await add_key(
                    request=request,
                    profile_id=1,
                    payload=payload,
                    db=db,
                    current_user=_make_user(1),
                )
        assert exc.value.status_code == 400
        assert "validation failed" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_rejects_write_enabled_key(self):
        db = AsyncMock()
        profile = _make_profile(profile_id=1, owner_id=1)
        db.get = AsyncMock(return_value=profile)

        payload = MagicMock()
        payload.exchange = "binance"
        payload.api_key = "test_key_12345678"
        payload.api_secret = "test_secret_12345678"

        request = MagicMock()
        request.app.state.http_client = None

        mock_adapter = AsyncMock()
        mock_adapter.validate_key = AsyncMock(
            side_effect=ValueError("Write permissions detected. Only read-only API keys are accepted.")
        )

        with patch("app.api.v1.keys.get_adapter", return_value=mock_adapter):
            with pytest.raises(HTTPException) as exc:
                await add_key(
                    request=request,
                    profile_id=1,
                    payload=payload,
                    db=db,
                    current_user=_make_user(1),
                )
        assert exc.value.status_code == 400
        assert "Write permissions" in exc.value.detail

    @pytest.mark.asyncio
    async def test_encrypts_key_before_storage(self):
        db = AsyncMock()
        profile = _make_profile(profile_id=1, owner_id=1)
        db.get = AsyncMock(return_value=profile)

        mock_key_obj = MagicMock()
        mock_key_obj.id = 10
        mock_key_obj.profile_id = 1
        mock_key_obj.exchange = "binance"

        payload = MagicMock()
        payload.exchange = "binance"
        payload.api_key = "plaintext_api_key_123"
        payload.api_secret = "plaintext_secret_456"

        request = MagicMock()
        request.app.state.http_client = None

        mock_adapter = AsyncMock()
        mock_adapter.validate_key = AsyncMock(return_value=True)

        with patch("app.api.v1.keys.get_adapter", return_value=mock_adapter):
            with patch("app.api.v1.keys.encrypt") as mock_encrypt:
                mock_encrypt.side_effect = lambda x: f"encrypted_{x}"
                with patch("app.api.v1.keys.ExchangeKey") as mock_exchange_key_cls:
                    mock_exchange_key_cls.return_value = mock_key_obj
                    db.refresh = AsyncMock()
                    await add_key(
                        request=request,
                        profile_id=1,
                        payload=payload,
                        db=db,
                        current_user=_make_user(1),
                    )

                # Verify encrypt was called with plaintext values
                mock_encrypt.assert_any_call("plaintext_api_key_123")
                mock_encrypt.assert_any_call("plaintext_secret_456")


class TestDeleteKey:
    @pytest.mark.asyncio
    async def test_returns_404_for_key_not_in_profile(self):
        profile = _make_profile(profile_id=1, owner_id=1)
        key_obj = MagicMock()
        key_obj.profile_id = 99  # different profile

        db = AsyncMock()
        # First call returns profile, second returns key
        db.get = AsyncMock(side_effect=[profile, key_obj])

        with pytest.raises(HTTPException) as exc:
            await delete_key(profile_id=1, key_id=5, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_key(self):
        profile = _make_profile(profile_id=1, owner_id=1)

        db = AsyncMock()
        db.get = AsyncMock(side_effect=[profile, None])

        with pytest.raises(HTTPException) as exc:
            await delete_key(profile_id=1, key_id=999, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404
