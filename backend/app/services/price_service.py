"""
Price service: fetch USD prices from exchange/market APIs.
Priority: Binance public API (no auth, 3500+ pairs) → CoinMarketCap (fallback) → $0
All prices are in USDT ≈ USD.
"""

import json
import logging

import httpx
import redis.asyncio as aioredis

from app.core.config import settings

_logger = logging.getLogger(__name__)

# Redis keys
_BINANCE_PRICE_CACHE_KEY = "binance:all_prices"
_BINANCE_PRICE_TTL = 30  # seconds
_CMC_PRICE_CACHE_KEY = "cmc:prices"
_CMC_PRICE_TTL = 120  # 2 minutes (CMC free tier has strict limits)


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


async def _fetch_cmc_prices(
    symbols: list[str],
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, float]:
    """Fetch USD prices from CoinMarketCap for specific symbols.

    Uses /v1/cryptocurrency/quotes/latest with symbol parameter.
    Free tier: 10,000 calls/month, up to 100 symbols per call.
    """
    if not settings.CMC_API_KEY:
        return {}

    if not symbols:
        return {}

    close = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10)
    try:
        # CMC accepts comma-separated symbols, max ~100 per request
        symbol_str = ",".join(symbols[:100])
        resp = await client.get(
            f"{settings.CMC_BASE_URL}/v1/cryptocurrency/quotes/latest",
            params={"symbol": symbol_str, "convert": "USD"},
            headers={
                "X-CMC_PRO_API_KEY": settings.CMC_API_KEY,
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        _logger.warning("CoinMarketCap price fetch failed: %s", e)
        return {}
    finally:
        if close:
            await client.aclose()

    prices: dict[str, float] = {}
    cmc_data = data.get("data", {})
    for symbol, entries in cmc_data.items():
        try:
            # CMC can return a list for symbols with multiple matches
            entry = entries[0] if isinstance(entries, list) else entries
            quote = entry.get("quote", {}).get("USD", {})
            price = quote.get("price")
            if price is not None and price > 0:
                prices[symbol.upper()] = float(price)
        except (KeyError, IndexError, TypeError, ValueError):
            continue

    return prices


async def get_usd_prices(
    assets: list[str],
    http_client: httpx.AsyncClient | None = None,
    redis_client: aioredis.Redis | None = None,
) -> dict[str, float]:
    """
    Return USD prices for the given asset symbols.
    Strategy: Binance public ticker (primary) → CoinMarketCap (fallback for missing).
    Redis caches both sources to avoid repeated fetches.
    """
    if not assets:
        return {}

    all_prices: dict[str, float] | None = None

    # ── 1. Try Binance (cached or fresh) ──────────────────────
    if redis_client is not None:
        try:
            cached = await redis_client.get(_BINANCE_PRICE_CACHE_KEY)
            if cached:
                all_prices = json.loads(cached)
        except Exception as e:
            _logger.warning("Redis price cache read failed: %s", e)

    if all_prices is None:
        all_prices = await _fetch_binance_all_prices(http_client)
        if all_prices and redis_client is not None:
            try:
                await redis_client.setex(
                    _BINANCE_PRICE_CACHE_KEY, _BINANCE_PRICE_TTL, json.dumps(all_prices)
                )
            except Exception as e:
                _logger.warning("Redis price cache write failed: %s", e)

    result = {asset: all_prices[asset] for asset in assets if asset in all_prices}

    # ── 2. CoinMarketCap fallback for missing assets ──────────
    missing = [a for a in assets if a not in result]
    if missing and settings.CMC_API_KEY:
        cmc_prices: dict[str, float] | None = None

        # Check CMC cache
        if redis_client is not None:
            try:
                cached = await redis_client.get(_CMC_PRICE_CACHE_KEY)
                if cached:
                    cmc_prices = json.loads(cached)
            except Exception:
                pass

        if cmc_prices is None:
            cmc_prices = await _fetch_cmc_prices(missing, http_client)
            if cmc_prices and redis_client is not None:
                try:
                    await redis_client.setex(
                        _CMC_PRICE_CACHE_KEY, _CMC_PRICE_TTL, json.dumps(cmc_prices)
                    )
                except Exception:
                    pass

        if cmc_prices:
            for asset in missing:
                if asset in cmc_prices:
                    result[asset] = cmc_prices[asset]
            _logger.info(
                "CMC fallback resolved %d/%d missing assets",
                sum(1 for a in missing if a in cmc_prices),
                len(missing),
            )

    return result
