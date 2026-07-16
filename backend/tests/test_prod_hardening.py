"""Tests for Redis-optional production hardening.

The live deployment may run without a reachable Redis (serverless without
REDIS_URL). Login must fall back to stateless HMAC state and portfolio reads
must degrade to uncached fetches instead of 500s.
"""

import os
import time

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.auth import (
    _STATELESS_PREFIX,
    google_login,
    make_stateless_state,
    verify_stateless_state,
)


class TestStatelessOAuthState:
    def test_roundtrip_valid(self):
        state = make_stateless_state()
        assert state.startswith(f"{_STATELESS_PREFIX}.")
        assert verify_stateless_state(state) is True

    def test_rejects_tampered_signature(self):
        state = make_stateless_state()
        parts = state.split(".")
        parts[-1] = ("0" * 32) if parts[-1] != "0" * 32 else ("1" * 32)
        assert verify_stateless_state(".".join(parts)) is False

    def test_rejects_tampered_expiry(self):
        state = make_stateless_state()
        prefix, nonce, expires, sig = state.split(".")
        assert verify_stateless_state(f"{prefix}.{nonce}.{int(expires) + 999}.{sig}") is False

    def test_rejects_expired(self):
        prefix = _STATELESS_PREFIX
        from app.api.v1.auth import _sign_state

        expired = int(time.time()) - 10
        state = f"{prefix}.nonce123.{expired}.{_sign_state('nonce123', expired)}"
        assert verify_stateless_state(state) is False

    def test_rejects_garbage(self):
        assert verify_stateless_state("not-a-state") is False
        assert verify_stateless_state("sl1.only.three") is False
        assert verify_stateless_state("") is False

    @pytest.mark.asyncio
    async def test_login_falls_back_to_stateless_when_redis_down(self):
        request = MagicMock()
        request.app.state.redis = AsyncMock()
        request.app.state.redis.set = AsyncMock(side_effect=ConnectionError("redis down"))
        request.base_url = "http://testserver/"

        with patch("app.api.v1.auth.settings") as mock_settings:
            mock_settings.BACKEND_URL = ""
            mock_settings.GOOGLE_CLIENT_ID = "cid"
            mock_settings.JWT_SECRET = os.environ["JWT_SECRET"]
            response = await google_login(request)

        location = response.headers["location"]
        assert f"state={_STATELESS_PREFIX}." in location


class TestPortfolioCacheDegradation:
    @pytest.mark.asyncio
    async def test_dead_redis_degrades_to_uncached_fetch(self):
        """get_portfolio must survive a Redis that raises on get/setex."""
        from app.services import portfolio_service

        dead_redis = AsyncMock()
        dead_redis.get = AsyncMock(side_effect=ConnectionError("refused"))
        dead_redis.setex = AsyncMock(side_effect=ConnectionError("refused"))

        key = MagicMock()
        key.exchange = "demo"
        key.key_type = "read_only"
        key.encrypted_key = "k"
        key.encrypted_secret = "s"
        key.id = 1
        key.profile_id = 1

        adapter = AsyncMock()
        balance = MagicMock()
        balance.asset = "BTC"
        balance.free = 1.0
        balance.locked = 0.0
        balance.total = 1.0
        adapter.get_balances = AsyncMock(return_value=[balance])

        with patch.object(portfolio_service, "decrypt", side_effect=lambda x: x):
            with patch.object(portfolio_service, "get_adapter", return_value=adapter):
                with patch.object(
                    portfolio_service, "get_usd_prices", AsyncMock(return_value={"BTC": 100.0})
                ):
                    result = await portfolio_service.get_portfolio(
                        1, "P", [key], redis=dead_redis
                    )

        assert result.total_usd == pytest.approx(100.0)
        assert result.cached is False
