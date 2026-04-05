"""
Price service: fetch USDT prices from exchange public APIs.
Priority: Binance public API (no auth, 3500+ pairs) → fallback $0
All prices are in USDT ≈ USD.
"""

import json
import logging

import httpx
import redis.asyncio as aioredis

_logger = logging.getLogger(__name__)

# Redis key for full Binance price map (all pairs)
_BINANCE_PRICE_CACHE_KEY = "binance:all_prices"
_BINANCE_PRICE_TTL = 30  # seconds


async def _fetch_binance_all_prices(
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, float]:
    """Fetch all USDT pairs from Binance public API (no auth required)."""
    close = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10)
    try:
        resp = await client.get("https://api.binance.com/api/v3/ticker/price")
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        _logger.warning("Binance price fetch failed: %s", e)
        return {}
    finally:
        if close:
            await client.aclose()

    prices: dict[str, float] = {}
    for item in data:
        symbol: str = item["symbol"]
        if symbol.endswith("USDT"):
            asset = symbol[:-4]  # strip "USDT"
            try:
                prices[asset] = float(item["price"])
            except (ValueError, KeyError):
                pass

    # Stablecoins
    prices["USDT"] = 1.0
    prices["USDC"] = 1.0
    prices["BUSD"] = 1.0
    prices["FDUSD"] = 1.0
    prices["TUSD"] = 1.0

    return prices


async def get_usd_prices(
    assets: list[str],
    http_client: httpx.AsyncClient | None = None,
    redis_client: aioredis.Redis | None = None,
) -> dict[str, float]:
    """
    Return USD prices for the given asset symbols.
    Uses Binance public ticker (no API key needed).
    Redis caches the full price map for 30s to avoid repeated fetches.
    """
    if not assets:
        return {}

    all_prices: dict[str, float] | None = None

    # Try Redis cache first
    if redis_client is not None:
        try:
            cached = await redis_client.get(_BINANCE_PRICE_CACHE_KEY)
            if cached:
                all_prices = json.loads(cached)
        except Exception as e:
            _logger.warning("Redis price cache read failed: %s", e)

    # Fetch from Binance if not cached
    if all_prices is None:
        all_prices = await _fetch_binance_all_prices(http_client)
        if all_prices and redis_client is not None:
            try:
                await redis_client.setex(
                    _BINANCE_PRICE_CACHE_KEY, _BINANCE_PRICE_TTL, json.dumps(all_prices)
                )
            except Exception as e:
                _logger.warning("Redis price cache write failed: %s", e)

    return {asset: all_prices[asset] for asset in assets if asset in all_prices}
