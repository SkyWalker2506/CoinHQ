"""
Portfolio service: fetch balances from all exchanges for a profile,
price them in USD via CoinGecko, cache results in Redis for 60s.
"""

import asyncio
import json
import logging

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import logger
from app.core.security import decrypt
from app.exchanges.factory import get_adapter
from app.models.exchange_key import ExchangeKey
from app.schemas.portfolio import (
    AggregatePortfolioResponse,
    Balance,
    ExchangeBalance,
    PortfolioResponse,
    ProfilePortfolio,
)

_stdlib_logger = logging.getLogger(__name__)

# CoinGecko symbol -> id mapping cache
_SYMBOL_TO_ID: dict[str, str] = {}


async def _get_usd_prices(
    assets: list[str],
    http_client: httpx.AsyncClient | None = None,
    redis: aioredis.Redis | None = None,
) -> dict[str, float]:
    """Fetch USD prices from CoinGecko free API, with optional 30s Redis cache."""
    if not assets:
        return {}

    cache_key = f"prices:{','.join(sorted(assets))}"
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            _stdlib_logger.warning("Redis price cache read failed: %s", e)

    # Common symbol overrides
    overrides = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "USDT": "tether",
        "USDC": "usd-coin",
        "SOL": "solana",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "TRX": "tron",
        "DOT": "polkadot",
        "MATIC": "matic-network",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "LTC": "litecoin",
        "UNI": "uniswap",
        "ATOM": "cosmos",
        "OP": "optimism",
        "ARB": "arbitrum",
        "SUI": "sui",
    }

    ids = []
    asset_to_id = {}
    for asset in assets:
        upper = asset.upper()
        if upper in overrides:
            cg_id = overrides[upper]
        else:
            cg_id = upper.lower()
        asset_to_id[upper] = cg_id
        ids.append(cg_id)

    try:
        client = http_client or httpx.AsyncClient(timeout=10)
        close_client = http_client is None
        try:
            resp = await client.get(
                f"{settings.COINGECKO_BASE_URL}/simple/price",
                params={"ids": ",".join(set(ids)), "vs_currencies": "usd"},
            )
            resp.raise_for_status()
            data = resp.json()
        finally:
            if close_client:
                await client.aclose()
    except Exception as e:
        _stdlib_logger.warning("CoinGecko price fetch failed: %s", e)
        return {}

    prices: dict[str, float] = {}
    for asset, cg_id in asset_to_id.items():
        price = data.get(cg_id, {}).get("usd")
        if price is not None:
            prices[asset] = float(price)

    # Cache prices for 30 seconds (COIN-22)
    if redis is not None:
        try:
            await redis.setex(cache_key, 30, json.dumps(prices))
        except Exception as e:
            _stdlib_logger.warning("Redis price cache write failed: %s", e)

    return prices


async def _fetch_exchange_balance(
    key: ExchangeKey,
    http_client: httpx.AsyncClient | None = None,
) -> list | None:
    """Decrypt keys and fetch raw balances from an exchange (no pricing)."""
    try:
        api_key = decrypt(key.encrypted_key)
        api_secret = decrypt(key.encrypted_secret)
        adapter = get_adapter(key.exchange, api_key, api_secret, http_client=http_client)
        balances = await adapter.get_balances()
        logger.info("api_key_used", key_id=key.id, exchange=key.exchange, profile_id=key.profile_id)
        return (key.exchange, balances)
    except Exception as e:
        _stdlib_logger.error("Failed to fetch balance from %s: %s", key.exchange, e)
        return None


def _build_exchange_balance(exchange: str, balances: list, prices: dict[str, float]) -> ExchangeBalance:
    """Apply prices to raw balances and return ExchangeBalance."""
    total_usd = 0.0
    priced_balances = []
    for b in balances:
        usd_val = prices.get(b.asset, 0.0) * b.total
        total_usd += usd_val
        priced_balances.append(
            Balance(
                asset=b.asset,
                free=b.free,
                locked=b.locked,
                total=b.total,
                usd_value=usd_val,
            )
        )
    return ExchangeBalance(
        exchange=exchange,
        balances=priced_balances,
        total_usd=total_usd,
    )


async def get_portfolio(
    profile_id: int,
    profile_name: str,
    keys: list[ExchangeKey],
    redis: aioredis.Redis | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> PortfolioResponse:
    """Get portfolio for a single profile with Redis caching."""
    cache_key = f"portfolio:profile:{profile_id}"

    if redis is not None:
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            data["cached"] = True
            return PortfolioResponse(**data)

    # Fetch all exchange balances in parallel
    raw_results = await asyncio.gather(
        *[_fetch_exchange_balance(key, http_client=http_client) for key in keys],
        return_exceptions=True,
    )

    # Collect all assets for a single bulk price request (COIN-13)
    exchange_raw: list[tuple] = []
    all_assets: list[str] = []
    for result in raw_results:
        if isinstance(result, Exception):
            _stdlib_logger.error("Exchange balance fetch raised exception: %s", result)
            continue
        if result is not None:
            exchange_name, balances = result
            exchange_raw.append((exchange_name, balances))
            all_assets.extend(b.asset for b in balances)

    prices = await _get_usd_prices(list(set(all_assets)), http_client=http_client, redis=redis)

    exchange_balances = [
        _build_exchange_balance(exchange_name, balances, prices)
        for exchange_name, balances in exchange_raw
    ]

    total_usd = sum(eb.total_usd for eb in exchange_balances)

    response = PortfolioResponse(
        profile_id=profile_id,
        profile_name=profile_name,
        exchanges=exchange_balances,
        total_usd=total_usd,
        cached=False,
    )

    if redis is not None:
        await redis.setex(
            cache_key,
            settings.PORTFOLIO_CACHE_TTL,
            response.model_dump_json(),
        )

    return response


async def get_aggregate_portfolio(
    profiles: list[tuple],  # List of (profile, keys)
    redis: aioredis.Redis | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> AggregatePortfolioResponse:
    """Get aggregate portfolio across all profiles (parallel fetch)."""
    # Fetch all profiles in parallel to avoid N+1 sequential awaits
    results = await asyncio.gather(
        *[
            get_portfolio(profile.id, profile.name, keys, redis=redis, http_client=http_client)
            for profile, keys in profiles
        ],
        return_exceptions=True,
    )

    profile_portfolios = []
    asset_totals: dict[str, float] = {}
    grand_total = 0.0

    for (profile, _), result in zip(profiles, results):
        if isinstance(result, Exception):
            _stdlib_logger.error("Failed to fetch portfolio for profile %s: %s", profile.id, result)
            continue

        portfolio = result
        grand_total += portfolio.total_usd

        pp = ProfilePortfolio(
            profile_id=profile.id,
            profile_name=profile.name,
            total_usd=portfolio.total_usd,
            exchanges=portfolio.exchanges,
        )
        profile_portfolios.append(pp)

        for exchange in portfolio.exchanges:
            for balance in exchange.balances:
                asset_totals[balance.asset] = (
                    asset_totals.get(balance.asset, 0.0) + (balance.usd_value or 0.0)
                )

    return AggregatePortfolioResponse(
        profiles=profile_portfolios,
        grand_total_usd=grand_total,
        asset_totals=asset_totals,
    )
