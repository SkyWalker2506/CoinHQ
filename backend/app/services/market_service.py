"""
Market data service: global metrics, coin info, and 24h change data from CoinMarketCap.
All data is cached in Redis to respect CMC free tier limits (10K calls/month).
"""

import json
import logging

import httpx
import redis.asyncio as aioredis

from app.core.config import settings

_logger = logging.getLogger(__name__)

_GLOBAL_METRICS_KEY = "cmc:global_metrics"
_GLOBAL_METRICS_TTL = 300  # 5 minutes

_COIN_INFO_KEY_PREFIX = "cmc:coin_info:"
_COIN_INFO_TTL = 86400  # 24 hours (static data)

_MARKET_DATA_KEY = "cmc:market_data"
_MARKET_DATA_TTL = 120  # 2 minutes


def _cmc_headers() -> dict[str, str]:
    return {
        "X-CMC_PRO_API_KEY": settings.CMC_API_KEY,
        "Accept": "application/json",
    }


async def get_global_metrics(
    http_client: httpx.AsyncClient | None = None,
    redis_client: aioredis.Redis | None = None,
) -> dict | None:
    """Fetch global crypto market metrics (total market cap, BTC dominance, etc.)."""
    if not settings.CMC_API_KEY:
        return None

    # Cache check
    if redis_client:
        try:
            cached = await redis_client.get(_GLOBAL_METRICS_KEY)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    close = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10)
    try:
        resp = await client.get(
            f"{settings.CMC_BASE_URL}/v1/global-metrics/quotes/latest",
            headers=_cmc_headers(),
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        _logger.warning("CMC global metrics fetch failed: %s", e)
        return None
    finally:
        if close:
            await client.aclose()

    data = raw.get("data", {})
    quote = data.get("quote", {}).get("USD", {})

    result = {
        "total_market_cap": quote.get("total_market_cap"),
        "total_volume_24h": quote.get("total_volume_24h"),
        "btc_dominance": data.get("btc_dominance"),
        "eth_dominance": data.get("eth_dominance"),
        "active_cryptocurrencies": data.get("active_cryptocurrencies"),
        "total_market_cap_change_24h": quote.get("total_market_cap_yesterday_percentage_change"),
    }

    if redis_client:
        try:
            await redis_client.setex(_GLOBAL_METRICS_KEY, _GLOBAL_METRICS_TTL, json.dumps(result))
        except Exception:
            pass

    return result


async def get_market_data(
    limit: int = 100,
    http_client: httpx.AsyncClient | None = None,
    redis_client: aioredis.Redis | None = None,
) -> dict[str, dict] | None:
    """Fetch top N coins with 24h change, market cap, volume.
    Returns dict keyed by symbol: {symbol: {price, change_24h, change_7d, market_cap, volume_24h, rank}}
    """
    if not settings.CMC_API_KEY:
        return None

    cache_key = f"{_MARKET_DATA_KEY}:{limit}"
    if redis_client:
        try:
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    close = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10)
    try:
        resp = await client.get(
            f"{settings.CMC_BASE_URL}/v1/cryptocurrency/listings/latest",
            params={"limit": limit, "convert": "USD"},
            headers=_cmc_headers(),
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        _logger.warning("CMC market data fetch failed: %s", e)
        return None
    finally:
        if close:
            await client.aclose()

    result: dict[str, dict] = {}
    for coin in raw.get("data", []):
        symbol = coin.get("symbol", "").upper()
        quote = coin.get("quote", {}).get("USD", {})
        result[symbol] = {
            "name": coin.get("name"),
            "symbol": symbol,
            "rank": coin.get("cmc_rank"),
            "price": quote.get("price"),
            "change_1h": quote.get("percent_change_1h"),
            "change_24h": quote.get("percent_change_24h"),
            "change_7d": quote.get("percent_change_7d"),
            "market_cap": quote.get("market_cap"),
            "volume_24h": quote.get("volume_24h"),
        }

    if redis_client and result:
        try:
            await redis_client.setex(cache_key, _MARKET_DATA_TTL, json.dumps(result))
        except Exception:
            pass

    return result


async def get_coin_info(
    symbols: list[str],
    http_client: httpx.AsyncClient | None = None,
    redis_client: aioredis.Redis | None = None,
) -> dict[str, dict] | None:
    """Fetch coin metadata: description, logo, website, tags.
    Uses /v1/cryptocurrency/info endpoint.
    """
    if not settings.CMC_API_KEY or not symbols:
        return None

    # Check per-symbol cache
    result: dict[str, dict] = {}
    missing: list[str] = []

    if redis_client:
        for symbol in symbols:
            try:
                cached = await redis_client.get(f"{_COIN_INFO_KEY_PREFIX}{symbol}")
                if cached:
                    result[symbol] = json.loads(cached)
                else:
                    missing.append(symbol)
            except Exception:
                missing.append(symbol)
    else:
        missing = list(symbols)

    if not missing:
        return result

    close = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10)
    try:
        resp = await client.get(
            f"{settings.CMC_BASE_URL}/v2/cryptocurrency/info",
            params={"symbol": ",".join(missing[:100])},
            headers=_cmc_headers(),
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception as e:
        _logger.warning("CMC coin info fetch failed: %s", e)
        return result if result else None
    finally:
        if close:
            await client.aclose()

    for symbol, entries in raw.get("data", {}).items():
        try:
            entry = entries[0] if isinstance(entries, list) else entries
            info = {
                "name": entry.get("name"),
                "symbol": entry.get("symbol", symbol).upper(),
                "slug": entry.get("slug"),
                "description": entry.get("description"),
                "logo": entry.get("logo"),
                "website": (entry.get("urls", {}).get("website") or [None])[0],
                "explorer": (entry.get("urls", {}).get("explorer") or [None])[0],
                "twitter": (entry.get("urls", {}).get("twitter") or [None])[0],
                "tags": [t.get("name") if isinstance(t, dict) else t for t in (entry.get("tags") or [])[:10]],
                "date_added": entry.get("date_added"),
                "category": entry.get("category"),
            }
            result[symbol.upper()] = info

            # Cache individual coin info
            if redis_client:
                try:
                    await redis_client.setex(
                        f"{_COIN_INFO_KEY_PREFIX}{symbol.upper()}",
                        _COIN_INFO_TTL,
                        json.dumps(info),
                    )
                except Exception:
                    pass
        except (KeyError, IndexError, TypeError):
            continue

    return result
