"""
Tests for portfolio_service — COIN-29
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Provide required env vars before importing modules that load config
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from app.services.portfolio_service import get_portfolio


def _make_key(exchange: str) -> MagicMock:
    key = MagicMock()
    key.exchange = exchange
    return key


def _make_balance(asset: str, free: float = 0.1, locked: float = 0.0):
    b = MagicMock()
    b.asset = asset
    b.free = free
    b.locked = locked
    b.total = free + locked
    return b


@pytest.mark.asyncio
async def test_get_portfolio_parallel_exchange_calls():
    """Exchange calls should be made in parallel with asyncio.gather"""
    call_count = 0

    async def mock_fetch_balance(key, http_client=None):
        nonlocal call_count
        call_count += 1
        return (key.exchange, [_make_balance("BTC")])

    with patch("app.services.portfolio_service._fetch_exchange_balance", side_effect=mock_fetch_balance):
        with patch(
            "app.services.portfolio_service.get_usd_prices",
            return_value={"BTC": 65000.0},
        ):
            mock_keys = [_make_key("binance"), _make_key("bybit")]
            await get_portfolio(1, "test", mock_keys, redis=None)

    assert call_count == 2  # Both exchanges called


@pytest.mark.asyncio
async def test_get_portfolio_single_coingecko_call():
    """CoinGecko should be called once regardless of exchange count"""
    coingecko_calls = 0

    async def mock_prices(assets, http_client=None, redis_client=None):
        nonlocal coingecko_calls
        coingecko_calls += 1
        return {"ETH": 3500.0}

    async def mock_fetch(key, http_client=None):
        return (key.exchange, [_make_balance("ETH")])

    with patch("app.services.portfolio_service.get_usd_prices", side_effect=mock_prices):
        with patch("app.services.portfolio_service._fetch_exchange_balance", side_effect=mock_fetch):
            mock_keys = [_make_key("binance"), _make_key("bybit"), _make_key("okx")]
            await get_portfolio(1, "test", mock_keys, redis=None)

    assert coingecko_calls == 1  # Only 1 CoinGecko call for all exchanges


@pytest.mark.asyncio
async def test_portfolio_exchange_failure_doesnt_break_others():
    """If one exchange fails, others should still return data"""

    async def mock_fetch(key, http_client=None):
        if key.exchange == "binance":
            raise Exception("Binance API error")
        return (key.exchange, [_make_balance("ETH", free=1.0)])

    with patch("app.services.portfolio_service._fetch_exchange_balance", side_effect=mock_fetch):
        with patch(
            "app.services.portfolio_service.get_usd_prices",
            return_value={"ETH": 3500.0},
        ):
            mock_keys = [_make_key("binance"), _make_key("bybit")]
            result = await get_portfolio(1, "test", mock_keys, redis=None)

    # bybit should still have data even though binance failed
    assert result is not None
    exchange_names = [e.exchange for e in result.exchanges]
    assert "bybit" in exchange_names
    assert "binance" not in exchange_names


@pytest.mark.asyncio
async def test_get_portfolio_uses_redis_cache():
    """Cached portfolio should be returned from Redis without exchange calls"""
    import json

    cached_data = {
        "profile_id": 1,
        "profile_name": "test",
        "exchanges": [],
        "total_usd": 999.0,
        "cached": False,
    }

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

    fetch_called = False

    async def mock_fetch(key, http_client=None):
        nonlocal fetch_called
        fetch_called = True
        return (key.exchange, [])

    with patch("app.services.portfolio_service._fetch_exchange_balance", side_effect=mock_fetch):
        result = await get_portfolio(1, "test", [_make_key("binance")], redis=mock_redis)

    assert not fetch_called  # Exchange was not called because cache hit
    assert result.total_usd == 999.0
    assert result.cached is True
