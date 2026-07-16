"""
Price service: fetch USDT prices from exchange public APIs.
Priority: Binance public API (no auth, 3500+ pairs) → CoinGecko fallback → $0
All prices are in USDT ≈ USD.
"""

import json
import logging

import httpx
import redis.asyncio as aioredis

from app.core.config import settings

_logger = logging.getLogger(__name__)

# Redis key for full Binance price map (all pairs)
_BINANCE_PRICE_CACHE_KEY = "binance:all_prices"
_BINANCE_PRICE_TTL = 30  # seconds

# Redis key for CoinGecko symbol→id map (large and stable, cache 24h)
# v2: bump after adding curated id overrides so poisoned cached maps expire.
_CG_COIN_LIST_CACHE_KEY = "coingecko:coin_list:v2"
_CG_COIN_LIST_TTL = 86_400  # 24 hours

# /coins/list is ordered alphabetically by id, NOT by market cap, so "first
# match wins" can resolve a major symbol to a dust token (e.g. BTC → some
# scam coin at $0.000005). Pin the majors to their canonical CoinGecko ids.
_CG_ID_OVERRIDES: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "TRX": "tron",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "LTC": "litecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "SHIB": "shiba-inu",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "XLM": "stellar",
    "ETC": "ethereum-classic",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "TON": "the-open-network",
    "PEPE": "pepe",
}

# Stablecoins are $1 regardless of price source.
_STABLECOINS = {"USDT": 1.0, "USDC": 1.0, "BUSD": 1.0, "FDUSD": 1.0, "TUSD": 1.0, "DAI": 1.0}

# Redis key prefix for CoinGecko per-coin USD prices
_CG_PRICE_CACHE_PREFIX = "coingecko:price:"
_CG_PRICE_TTL = 60  # seconds — consistent with Binance TTL range


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


async def _get_coingecko_symbol_map(
    http_client: httpx.AsyncClient,
    redis_client: aioredis.Redis | None,
) -> dict[str, str]:
    """
    Return a symbol→coingecko_id map built from /coins/list.

    Disambiguation heuristic (best-effort fallback — not authoritative):
      1. If an id exactly equals the lowercased symbol, prefer it.
      2. Otherwise take the first match in the list (CoinGecko returns by
         market-cap rank descending for well-known coins, so the first hit
         is usually the most prominent one).
    This is intentionally simple; the goal is to price dust/low-cap holdings
    that Binance doesn't list, not to be a canonical coin registry.
    """
    # Try Redis cache
    if redis_client is not None:
        try:
            cached = await redis_client.get(_CG_COIN_LIST_CACHE_KEY)
            if cached:
                return json.loads(cached)
        except Exception as e:
            _logger.warning("Redis CoinGecko coin-list cache read failed: %s", e)

    try:
        resp = await http_client.get(
            f"{settings.COINGECKO_BASE_URL}/coins/list",
            timeout=15,
        )
        resp.raise_for_status()
        coins: list[dict[str, str]] = resp.json()
    except Exception as e:
        _logger.warning("CoinGecko /coins/list fetch failed: %s", e)
        return {}

    symbol_map: dict[str, str] = {}
    for coin in coins:
        sym = coin.get("symbol", "").upper()
        cg_id = coin.get("id", "")
        if not sym or not cg_id:
            continue
        if sym not in symbol_map:
            # First occurrence wins unless a better match is found below
            symbol_map[sym] = cg_id
        elif cg_id == sym.lower():
            # Exact lowercase-symbol == id is the canonical/well-known coin
            symbol_map[sym] = cg_id

    # Curated overrides always win — the list is alphabetical, not market-cap,
    # so majors would otherwise resolve to dust tokens with the same symbol.
    symbol_map.update(_CG_ID_OVERRIDES)

    if symbol_map and redis_client is not None:
        try:
            await redis_client.setex(
                _CG_COIN_LIST_CACHE_KEY, _CG_COIN_LIST_TTL, json.dumps(symbol_map)
            )
        except Exception as e:
            _logger.warning("Redis CoinGecko coin-list cache write failed: %s", e)

    return symbol_map


async def _fetch_coingecko_prices(
    symbols: list[str],
    http_client: httpx.AsyncClient,
    redis_client: aioredis.Redis | None,
) -> dict[str, float]:
    """
    Fetch USD prices from CoinGecko for the given asset symbols.
    Returns a symbol→price dict for whatever was found.
    Errors are logged and swallowed — callers receive a partial/empty result.
    """
    if not symbols:
        return {}

    symbol_map = await _get_coingecko_symbol_map(http_client, redis_client)
    if not symbol_map:
        return {}

    # Map requested symbols to CoinGecko ids
    sym_to_id: dict[str, str] = {}
    for sym in symbols:
        cg_id = symbol_map.get(sym.upper())
        if cg_id:
            sym_to_id[sym] = cg_id

    if not sym_to_id:
        return {}

    # Check per-coin Redis cache first
    prices: dict[str, float] = {}
    uncached_syms: list[str] = []
    if redis_client is not None:
        for sym in sym_to_id:
            try:
                cached = await redis_client.get(f"{_CG_PRICE_CACHE_PREFIX}{sym}")
                if cached is not None:
                    prices[sym] = float(cached)
                else:
                    uncached_syms.append(sym)
            except Exception as e:
                _logger.warning("Redis CoinGecko price cache read failed: %s", e)
                uncached_syms.append(sym)
    else:
        uncached_syms = list(sym_to_id)

    if not uncached_syms:
        return prices

    ids_param = ",".join(sym_to_id[s] for s in uncached_syms)
    try:
        resp = await http_client.get(
            f"{settings.COINGECKO_BASE_URL}/simple/price",
            params={"ids": ids_param, "vs_currencies": "usd"},
            timeout=10,
        )
        if resp.status_code == 429:
            _logger.warning("CoinGecko rate-limited (429) — skipping fallback prices")
            return prices
        resp.raise_for_status()
        data: dict[str, dict[str, float]] = resp.json()
    except Exception as e:
        _logger.warning("CoinGecko /simple/price fetch failed: %s", e)
        return prices

    for sym in uncached_syms:
        cg_id = sym_to_id[sym]
        usd = data.get(cg_id, {}).get("usd")
        if usd is not None:
            prices[sym] = float(usd)
            if redis_client is not None:
                try:
                    await redis_client.setex(
                        f"{_CG_PRICE_CACHE_PREFIX}{sym}",
                        _CG_PRICE_TTL,
                        str(usd),
                    )
                except Exception as e:
                    _logger.warning(
                        "Redis CoinGecko price cache write failed for %s: %s", sym, e
                    )

    return prices


async def get_usd_prices(
    assets: list[str],
    http_client: httpx.AsyncClient | None = None,
    redis_client: aioredis.Redis | None = None,
) -> dict[str, float]:
    """
    Return USD prices for the given asset symbols.

    Primary:  Binance public ticker (no API key needed), cached in Redis 30s.
    Fallback: CoinGecko /simple/price for assets without a Binance USDT pair,
              cached per-coin in Redis 60s.
    Stablecoins are hardcoded to $1 and never sent to CoinGecko.
    Any CoinGecko error/timeout is logged and swallowed — never raised.
    """
    if not assets:
        return {}

    # Demo mode is fully offline & deterministic: no live Binance/CoinGecko calls,
    # so demos and E2E always see the same portfolio total.
    if settings.DEMO_MODE:
        from app.exchanges.demo import DEMO_PRICES
        return {a: DEMO_PRICES[a] for a in assets if a in DEMO_PRICES}

    close_client = http_client is None
    client = http_client or httpx.AsyncClient(timeout=10)

    try:
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
            all_prices = await _fetch_binance_all_prices(client)
            if all_prices and redis_client is not None:
                try:
                    await redis_client.setex(
                        _BINANCE_PRICE_CACHE_KEY,
                        _BINANCE_PRICE_TTL,
                        json.dumps(all_prices),
                    )
                except Exception as e:
                    _logger.warning("Redis price cache write failed: %s", e)

        result: dict[str, float] = {
            asset: all_prices[asset] for asset in assets if asset in all_prices
        }

        # Stablecoins are $1 regardless of source (also covers the case where
        # Binance is unreachable/geo-blocked and everything falls to CoinGecko).
        for asset in assets:
            if asset in _STABLECOINS:
                result[asset] = _STABLECOINS[asset]

        # CoinGecko fallback for assets that Binance didn't price
        unpriced = [a for a in assets if a not in result]
        if unpriced:
            cg_prices = await _fetch_coingecko_prices(unpriced, client, redis_client)
            result.update(cg_prices)

        return result

    finally:
        if close_client:
            await client.aclose()
