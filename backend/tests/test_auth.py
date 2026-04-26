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


class _StatefulRedisStub:
    """Minimal stateful Redis stub — supports set(ex=...), delete(), and a
    `_expire(key)` helper that simulates TTL expiry so we can exercise the
    real callback path against a simulated time-to-live event.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        # ex is recorded but not enforced — call _expire() to simulate TTL elapse
        self.store[key] = value
        return True

    async def delete(self, key: str) -> int:
        return 1 if self.store.pop(key, None) is not None else 0

    def _expire(self, key: str) -> None:
        """Test helper: simulate the TTL elapsing (key vanishes from Redis)."""
        self.store.pop(key, None)


class TestOAuthStateLifecycle:
    """Integration coverage for the OAuth state lifecycle:
    set with TTL → consume on callback → reject expired/replayed state.
    """

    @pytest.mark.asyncio
    async def test_expired_state_returns_403(self):
        """When Redis state TTL has elapsed, callback must return 403 even
        though the state value was originally legitimate."""
        from app.api.v1.auth import _state_key, google_login

        redis = _StatefulRedisStub()
        # Step 1: simulate /google → state stored with TTL
        login_request = _make_request_with_redis(redis)
        login_request.base_url = "http://test/"
        await google_login(request=login_request)
        assert len(redis.store) == 1
        state = next(iter(redis.store)).removeprefix("oauth_state:")
        assert state and len(state) >= 20  # token_urlsafe(32) ≥ 32 chars

        # Step 2: simulate TTL elapse (10-min window expired before user returned)
        redis._expire(_state_key(state))
        assert _state_key(state) not in redis.store

        # Step 3: callback with the now-expired state → 403
        callback_request = _make_request_with_redis(redis)
        with pytest.raises(HTTPException) as exc:
            await google_callback(
                request=callback_request,
                code="authcode-after-expiry",
                error=None,
                state=state,
                db=AsyncMock(),
            )
        assert exc.value.status_code == 403
        assert "CSRF" in exc.value.detail

    @pytest.mark.asyncio
    async def test_state_is_single_use(self):
        """A valid state is atomically consumed: replay must 403."""
        from app.api.v1.auth import _state_key, google_login

        redis = _StatefulRedisStub()
        login_request = _make_request_with_redis(redis)
        login_request.base_url = "http://test/"
        await google_login(request=login_request)
        state = next(iter(redis.store)).removeprefix("oauth_state:")

        # Manually consume the state (mimic a successful first callback)
        consumed = await redis.delete(_state_key(state))
        assert consumed == 1

        # Replay attempt → state already gone → 403
        with pytest.raises(HTTPException) as exc:
            await google_callback(
                request=_make_request_with_redis(redis),
                code="replay-code",
                error=None,
                state=state,
                db=AsyncMock(),
            )
        assert exc.value.status_code == 403


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
