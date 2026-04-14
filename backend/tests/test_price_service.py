"""Tests for services/price_service.py — Binance price fetching and Redis caching."""

import json
import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.price_service import _fetch_binance_all_prices, get_usd_prices


class TestFetchBinanceAllPrices:
    @pytest.mark.asyncio
    async def test_parses_usdt_pairs(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"symbol": "BTCUSDT", "price": "65000.50"},
            {"symbol": "ETHUSDT", "price": "3500.25"},
            {"symbol": "BTCETH", "price": "18.5"},  # not USDT pair
        ]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        prices = await _fetch_binance_all_prices(http_client=mock_client)

        assert prices["BTC"] == 65000.50
        assert prices["ETH"] == 3500.25
        assert "BTCETH" not in prices

    @pytest.mark.asyncio
    async def test_stablecoins_hardcoded(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        prices = await _fetch_binance_all_prices(http_client=mock_client)

        assert prices["USDT"] == 1.0
        assert prices["USDC"] == 1.0
        assert prices["BUSD"] == 1.0
        assert prices["FDUSD"] == 1.0
        assert prices["TUSD"] == 1.0

    @pytest.mark.asyncio
    async def test_returns_empty_on_api_failure(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection timeout"))

        prices = await _fetch_binance_all_prices(http_client=mock_client)
        assert prices == {}


class TestGetUsdPrices:
    @pytest.mark.asyncio
    async def test_empty_asset_list_returns_empty(self):
        result = await get_usd_prices([], redis_client=None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_cached_prices_from_redis(self):
        cached = json.dumps({"BTC": 70000.0, "ETH": 4000.0})
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached)

        result = await get_usd_prices(["BTC", "ETH"], redis_client=mock_redis)

        assert result == {"BTC": 70000.0, "ETH": 4000.0}

    @pytest.mark.asyncio
    async def test_fetches_from_binance_on_cache_miss(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        binance_data = [
            {"symbol": "BTCUSDT", "price": "65000.0"},
        ]

        mock_resp = MagicMock()
        mock_resp.json.return_value = binance_data
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.aclose = AsyncMock()

        result = await get_usd_prices(
            ["BTC"], http_client=mock_client, redis_client=mock_redis
        )

        assert result["BTC"] == 65000.0
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_read_failure_falls_back_to_fetch(self):
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=Exception("Redis down"))
        mock_redis.setex = AsyncMock(side_effect=Exception("Redis down"))

        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"symbol": "ETHUSDT", "price": "3500.0"}]
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.aclose = AsyncMock()

        result = await get_usd_prices(
            ["ETH"], http_client=mock_client, redis_client=mock_redis
        )

        assert result["ETH"] == 3500.0

    @pytest.mark.asyncio
    async def test_filters_only_requested_assets(self):
        cached = json.dumps({"BTC": 70000.0, "ETH": 4000.0, "SOL": 150.0})
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=cached)

        result = await get_usd_prices(["BTC", "DOGE"], redis_client=mock_redis)

        assert "BTC" in result
        assert "DOGE" not in result
        assert "ETH" not in result
