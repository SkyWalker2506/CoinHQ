"""
Portfolio service: fetch balances from all exchanges for a profile,
price them in USD via CoinGecko, cache results in Redis for 60s.
"""

import json
import logging
from typing import List, Dict, Optional

import httpx

from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.security import decrypt
from app.exchanges.factory import get_adapter
from app.models.exchange_key import ExchangeKey
from app.schemas.portfolio import (
    Balance,
    ExchangeBalance,
    PortfolioResponse,
    AggregatePortfolioResponse,
    ProfilePortfolio,
)

logger = logging.getLogger(__name__)

# CoinGecko symbol -> id mapping cache
_SYMBOL_TO_ID: Dict[str, str] = {}


async def _get_usd_prices(assets: List[str]) -> Dict[str, float]:
    """Fetch USD prices from CoinGecko free API."""
    if not assets:
        return {}

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
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{settings.COINGECKO_BASE_URL}/simple/price",
                params={"ids": ",".join(set(ids)), "vs_currencies": "usd"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("CoinGecko price fetch failed: %s", e)
        return {}

    prices: Dict[str, float] = {}
    for asset, cg_id in asset_to_id.items():
        price = data.get(cg_id, {}).get("usd")
        if price is not None:
            prices[asset] = float(price)

    return prices


async def _fetch_exchange_balance(
    key: ExchangeKey,
) -> Optional[ExchangeBalance]:
    """Decrypt keys and fetch balances from an exchange."""
    try:
        api_key = decrypt(key.encrypted_key)
        api_secret = decrypt(key.encrypted_secret)
        adapter = get_adapter(key.exchange, api_key, api_secret)
        balances = await adapter.get_balances()

        # Get USD prices
        assets = [b.asset for b in balances]
        prices = await _get_usd_prices(assets)

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
            exchange=key.exchange,
            balances=priced_balances,
            total_usd=total_usd,
        )
    except Exception as e:
        logger.error("Failed to fetch balance from %s: %s", key.exchange, e)
        return None


async def get_portfolio(
    profile_id: int,
    profile_name: str,
    keys: List[ExchangeKey],
) -> PortfolioResponse:
    """Get portfolio for a single profile with Redis caching."""
    redis = await get_redis()
    cache_key = f"portfolio:profile:{profile_id}"

    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return PortfolioResponse(**data)

    exchange_balances = []
    for key in keys:
        result = await _fetch_exchange_balance(key)
        if result:
            exchange_balances.append(result)

    total_usd = sum(eb.total_usd for eb in exchange_balances)

    response = PortfolioResponse(
        profile_id=profile_id,
        profile_name=profile_name,
        exchanges=exchange_balances,
        total_usd=total_usd,
        cached=False,
    )

    await redis.setex(
        cache_key,
        settings.PORTFOLIO_CACHE_TTL,
        response.model_dump_json(),
    )

    return response


async def get_aggregate_portfolio(
    profiles: List[tuple],  # List of (profile, keys)
) -> AggregatePortfolioResponse:
    """Get aggregate portfolio across all profiles."""
    profile_portfolios = []
    asset_totals: Dict[str, float] = {}
    grand_total = 0.0

    for profile, keys in profiles:
        portfolio = await get_portfolio(profile.id, profile.name, keys)
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
