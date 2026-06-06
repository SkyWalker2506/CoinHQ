"""Tests for services/price_service.py — Binance price fetching and Redis caching."""

import json
import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from unittest.mock import AsyncMock, MagicMock

import httpx
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


# ---------------------------------------------------------------------------
# CoinGecko fallback tests
# ---------------------------------------------------------------------------


def _make_binance_resp(pairs: list[tuple[str, str]]) -> MagicMock:
    """Build a mock Binance ticker response for the given (symbol, price) pairs."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = [
        {"symbol": sym, "price": price} for sym, price in pairs
    ]
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_cg_coins_resp(coins: list[dict]) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = coins
    mock_resp.raise_for_status = MagicMock()
    mock_resp.status_code = 200
    return mock_resp


def _make_cg_price_resp(data: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    mock_resp.status_code = 200
    return mock_resp


class TestCoinGeckoFallback:
    """
    Tests for the CoinGecko fallback path in get_usd_prices.
    All tests mock HTTP responses — no real network calls.
    """

    @pytest.mark.asyncio
    async def test_asset_on_binance_not_priced_via_coingecko(self):
        """Asset present on Binance → priced via Binance, CoinGecko NOT called."""
        binance_resp = _make_binance_resp([("BTCUSDT", "65000.0")])

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "binance.com" in url:
                return binance_resp
            raise AssertionError(f"Unexpected URL called: {url}")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        result = await get_usd_prices(
            ["BTC"], http_client=mock_client, redis_client=mock_redis
        )

        assert result["BTC"] == 65000.0
        # Only Binance was called (1 call)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_asset_missing_on_binance_priced_via_coingecko(self):
        """Asset missing on Binance but present on CoinGecko → priced via CoinGecko."""
        binance_resp = _make_binance_resp([])  # no USDT pairs at all

        coin_list_resp = _make_cg_coins_resp(
            [{"id": "mytoken", "symbol": "MTK", "name": "MyToken"}]
        )
        cg_price_resp = _make_cg_price_resp({"mytoken": {"usd": 0.042}})

        call_responses = {
            "binance.com": binance_resp,
            "coins/list": coin_list_resp,
            "simple/price": cg_price_resp,
        }

        async def mock_get(url, **kwargs):
            for key, resp in call_responses.items():
                if key in url:
                    return resp
            raise AssertionError(f"Unexpected URL: {url}")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        result = await get_usd_prices(
            ["MTK"], http_client=mock_client, redis_client=mock_redis
        )

        assert result["MTK"] == pytest.approx(0.042)

    @pytest.mark.asyncio
    async def test_coingecko_error_leaves_asset_unpriced_no_exception(self):
        """CoinGecko error/timeout → asset left unpriced, no exception raised."""
        binance_resp = _make_binance_resp([])  # no pairs

        call_count = {"coins_list": 0}

        async def mock_get(url, **kwargs):
            if "binance.com" in url:
                return binance_resp
            if "coins/list" in url:
                call_count["coins_list"] += 1
                raise httpx.TimeoutException("timeout")
            raise AssertionError(f"Unexpected URL: {url}")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        # Must not raise
        result = await get_usd_prices(
            ["UNKNOWNCOIN"], http_client=mock_client, redis_client=mock_redis
        )

        assert "UNKNOWNCOIN" not in result
        assert call_count["coins_list"] == 1

    @pytest.mark.asyncio
    async def test_coingecko_rate_limit_leaves_asset_unpriced_no_exception(self):
        """CoinGecko 429 → asset left unpriced, no exception raised."""
        binance_resp = _make_binance_resp([])

        coin_list_resp = _make_cg_coins_resp(
            [{"id": "mytoken", "symbol": "MTK", "name": "MyToken"}]
        )

        rate_limit_resp = MagicMock()
        rate_limit_resp.status_code = 429
        rate_limit_resp.raise_for_status = MagicMock()

        async def mock_get(url, **kwargs):
            if "binance.com" in url:
                return binance_resp
            if "coins/list" in url:
                return coin_list_resp
            if "simple/price" in url:
                return rate_limit_resp
            raise AssertionError(f"Unexpected URL: {url}")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        result = await get_usd_prices(
            ["MTK"], http_client=mock_client, redis_client=mock_redis
        )

        assert "MTK" not in result

    @pytest.mark.asyncio
    async def test_symbol_to_id_map_cached_in_redis(self):
        """CoinGecko symbol→id map is written to Redis and read from cache on second call."""
        binance_resp = _make_binance_resp([])

        coin_list_resp = _make_cg_coins_resp(
            [{"id": "mytoken", "symbol": "MTK", "name": "MyToken"}]
        )
        cg_price_resp = _make_cg_price_resp({"mytoken": {"usd": 1.5}})

        # Simulate: first call has no Binance cache and no CoinGecko coin-list cache
        get_call_count = {"coins_list": 0}

        async def mock_get(url, **kwargs):
            if "binance.com" in url:
                return binance_resp
            if "coins/list" in url:
                get_call_count["coins_list"] += 1
                return coin_list_resp
            if "simple/price" in url:
                return cg_price_resp
            raise AssertionError(f"Unexpected URL: {url}")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        setex_calls: list[str] = []

        async def mock_setex(key, ttl, value):
            setex_calls.append(key)

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = mock_setex

        await get_usd_prices(["MTK"], http_client=mock_client, redis_client=mock_redis)

        # The coin-list cache key must have been written
        assert any("coin_list" in k for k in setex_calls), (
            f"coin_list key not in setex calls: {setex_calls}"
        )
        # /coins/list was fetched exactly once
        assert get_call_count["coins_list"] == 1

    @pytest.mark.asyncio
    async def test_symbol_id_disambiguation_exact_match_preferred(self):
        """
        When multiple coins share a ticker, the one whose id == lowercased symbol
        is preferred over the first match.
        """
        binance_resp = _make_binance_resp([])

        # 'xrp' appears first as 'xrp-legacy' then the canonical 'xrp'
        coin_list_resp = _make_cg_coins_resp(
            [
                {"id": "xrp-legacy", "symbol": "XRP", "name": "XRP Legacy"},
                {"id": "xrp", "symbol": "XRP", "name": "XRP"},
            ]
        )
        # Only the canonical id 'xrp' will be queried
        cg_price_resp = _make_cg_price_resp({"xrp": {"usd": 0.5}})

        async def mock_get(url, **kwargs):
            if "binance.com" in url:
                return binance_resp
            if "coins/list" in url:
                return coin_list_resp
            if "simple/price" in url:
                # Verify the canonical id was sent
                params = kwargs.get("params", {})
                assert "xrp" in params.get("ids", ""), (
                    f"Expected canonical id 'xrp' in ids, got: {params}"
                )
                return cg_price_resp
            raise AssertionError(f"Unexpected URL: {url}")

        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.aclose = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.setex = AsyncMock()

        result = await get_usd_prices(
            ["XRP"], http_client=mock_client, redis_client=mock_redis
        )

        assert result["XRP"] == pytest.approx(0.5)
