"""Tests for api/v1/auth.py — OAuth flow and token refresh."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.auth import (
    RefreshRequest,
    google_callback,
    refresh_access_token,
)
from app.core.security import create_access_token, create_refresh_token


def _make_request_with_redis(redis_mock: AsyncMock) -> MagicMock:
    """Build a mock Request whose app.state.redis is the given mock."""
    request = MagicMock()
    request.app.state.redis = redis_mock
    return request


class TestGoogleCallback:
    @pytest.mark.asyncio
    async def test_rejects_missing_code(self):
        redis = AsyncMock()
        request = _make_request_with_redis(redis)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await google_callback(request=request, code=None, error=None, state=None, db=db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_rejects_oauth_error(self):
        redis = AsyncMock()
        request = _make_request_with_redis(redis)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await google_callback(
                request=request, code=None, error="access_denied", state=None, db=db
            )
        assert exc.value.status_code == 401
        assert "access_denied" in str(exc.value.detail)

    @pytest.mark.asyncio
    async def test_rejects_none_state(self):
        """state=None raises 403 before even touching Redis."""
        redis = AsyncMock()
        request = _make_request_with_redis(redis)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await google_callback(
                request=request, code="authcode123", error=None, state=None, db=db
            )
        assert exc.value.status_code == 403
        assert "CSRF" in exc.value.detail

    @pytest.mark.asyncio
    async def test_rejects_invalid_state(self):
        """Redis returns 0 (key not found) → 403 CSRF."""
        redis = AsyncMock()
        redis.delete = AsyncMock(return_value=0)  # key not in Redis
        request = _make_request_with_redis(redis)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await google_callback(
                request=request, code="authcode123", error=None, state="bad-state", db=db
            )
        assert exc.value.status_code == 403
        assert "CSRF" in exc.value.detail


class TestRefreshAccessToken:
    @pytest.mark.asyncio
    async def test_valid_refresh_token_returns_new_access_token(self):
        refresh = create_refresh_token(user_id=42)
        body = RefreshRequest(refresh_token=refresh)

        result = await refresh_access_token(body)
        assert "access_token" in result
        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_invalid_refresh_token_raises_401(self):
        body = RefreshRequest(refresh_token="invalid.token.here")

        with pytest.raises(HTTPException) as exc:
            await refresh_access_token(body)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_access_token_as_refresh_raises_401(self):
        access = create_access_token(user_id=1)
        body = RefreshRequest(refresh_token=access)

        with pytest.raises(HTTPException) as exc:
            await refresh_access_token(body)
        assert exc.value.status_code == 401
