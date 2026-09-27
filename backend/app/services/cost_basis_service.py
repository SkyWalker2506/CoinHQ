"""
Cost-basis service: average buy price per coin from each EXCHANGE's own trade
history (not CoinHQ's orders — see pnl_service for those).

Method: average cost (AVCO) over the venue's fills in time order.
  - Only fills quoted in a USD-stable asset count, valued at $1 per quote
    unit. A buy in any other quote (ADA/BTC, UNI/ETH) is skipped and marks
    the asset's coverage "partial".
  - A fee charged in the base asset reduces the quantity actually received;
    a fee charged in the quote raises the cost. Fees in anything else (BNB,
    GT, points) are ignored.
  - A sell releases quantity at the running average cost and never pushes
    the position negative — selling more than the fills explain just means
    the surplus came from a deposit.

Coverage compares the net quantity the fills explain with what the venue
holds right now: "full" when ≥ ~99 % of the balance is explained, "partial"
when less (deposits, transfers, truncated history, non-stable quotes), "none"
when no qualifying buy exists at all (avg_buy_price is then null).

Results are cached per profile for 15 minutes — in Redis when available and
in a process-local memo either way (production runs without Redis).
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx
import redis.asyncio as aioredis

from app.core.logging import logger
from app.core.security import decrypt
from app.exchanges.base import ExchangeAdapter, Fill
from app.exchanges.factory import get_adapter
from app.models.exchange_key import ExchangeKey
from app.schemas.cost_basis import AssetCostBasis, CostBasisResponse, ExchangeCostBasis
from app.schemas.portfolio import Balance
from app.services.portfolio_service import get_portfolio

_stdlib_logger = logging.getLogger(__name__)

STABLE_QUOTES = frozenset({"USDT", "USDC", "FDUSD", "BUSD", "TUSD", "DAI", "USD"})

COST_BASIS_CACHE_TTL = 15 * 60
# A venue that supports trade history but failed this time (timeout, 5xx,
# rate limit) must not be pinned as "unsupported" for the full window.
COST_BASIS_DEGRADED_TTL = 60
_FULL_COVERAGE_RATIO = 0.99
_EPS = 1e-12

# Process-local cache (mirrors price_service): Redis is optional in this
# deployment, and trade history is by far the most expensive thing we fetch.
_MEMO: dict[str, tuple[float, Any]] = {}


def _memo_get(key: str) -> Any | None:
    entry = _MEMO.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.time() > expires_at:
        _MEMO.pop(key, None)
        return None
    return value


def _memo_set(key: str, value: Any, ttl: int) -> None:
    _MEMO[key] = (time.time() + ttl, value)


def _cache_key(profile_id: int) -> str:
    return f"costbasis:profile:{profile_id}"


@dataclass
class _Position:
    qty: float = 0.0
    cost: float = 0.0
    bought_qty: float = 0.0
    has_buys: bool = False
    skipped_non_stable: bool = False
    _touched: list[str] = field(default_factory=list)


def compute_avco(fills: list[Fill], held: dict[str, float]) -> list[AssetCostBasis]:
    """AVCO over `fills` for every asset in `held` (asset → quantity on venue)."""
    positions: dict[str, _Position] = {asset: _Position() for asset in held}

    for f in sorted(fills, key=lambda x: x.ts_ms):
        pos = positions.get(f.asset)
        if pos is None:
            continue
        if f.quote_asset not in STABLE_QUOTES:
            pos.skipped_non_stable = True
            continue
        if f.qty <= 0:
            continue

        if f.side == "buy":
            received = f.qty
            cost = f.quote_qty
            if f.fee_asset == f.asset:
                received -= f.fee_qty
            elif f.fee_asset in STABLE_QUOTES:
                cost += f.fee_qty
            if received <= 0:
                continue
            pos.qty += received
            pos.cost += cost
            pos.bought_qty += received
            pos.has_buys = True
        elif f.side == "sell":
            sold = min(f.qty, pos.qty)
            if sold > 0 and pos.qty > _EPS:
                avg = pos.cost / pos.qty
                pos.cost -= sold * avg
                pos.qty -= sold
                if pos.qty <= _EPS:
                    pos.qty, pos.cost = 0.0, 0.0

    out: list[AssetCostBasis] = []
    for asset in sorted(positions):
        pos = positions[asset]
        held_qty = held[asset]
        if not pos.has_buys or pos.qty <= _EPS:
            out.append(AssetCostBasis(asset=asset, avg_buy_price=None,
                                      bought_qty=pos.bought_qty, coverage="none"))
            continue
        avg = pos.cost / pos.qty
        explained = held_qty <= 0 or pos.qty >= held_qty * _FULL_COVERAGE_RATIO
        coverage = "full" if explained and not pos.skipped_non_stable else "partial"
        out.append(AssetCostBasis(
            asset=asset,
            avg_buy_price=avg,
            bought_qty=pos.bought_qty,
            coverage=coverage,
        ))
    return out


def _dedupe_keys(keys: list[ExchangeKey]) -> dict[str, ExchangeKey]:
    """One key per exchange, preferring read_only — same rule as get_portfolio."""
    keys_by_exchange: dict[str, ExchangeKey] = {}
    for key in keys:
        existing = keys_by_exchange.get(key.exchange)
        if existing is None or (existing.key_type != "read_only" and key.key_type == "read_only"):
            keys_by_exchange[key.exchange] = key
    return keys_by_exchange


async def _exchange_cost_basis(
    key: ExchangeKey,
    balances: list[Balance],
    http_client: httpx.AsyncClient | None,
) -> tuple[ExchangeCostBasis, bool]:
    """Cost basis for one venue, plus whether a supported venue failed."""
    # Stablecoins have no meaningful buy price; dust is dropped by the
    # adapters' call budgets, so the most valuable assets go first.
    held_balances = sorted(
        (b for b in balances if b.total > 0 and b.asset.upper() not in STABLE_QUOTES),
        key=lambda b: b.usd_value or 0.0,
        reverse=True,
    )
    if not held_balances:
        return ExchangeCostBasis(exchange=key.exchange, supported=True, assets=[]), False

    api_key = decrypt(key.encrypted_key)
    api_secret = decrypt(key.encrypted_secret)
    adapter = get_adapter(key.exchange, api_key, api_secret, http_client=http_client)
    fills = await adapter.get_fills([b.asset for b in held_balances])
    if fills is None:
        # Only adapters that override get_fills can have *failed*; the base
        # default means the venue genuinely has no trade history here.
        failed = type(adapter).get_fills is not ExchangeAdapter.get_fills
        return ExchangeCostBasis(exchange=key.exchange, supported=False, assets=[]), failed
    logger.info("api_key_used", key_id=key.id, exchange=key.exchange,
                profile_id=key.profile_id, purpose="fills")

    held = {b.asset: b.total for b in held_balances}
    return ExchangeCostBasis(
        exchange=key.exchange, supported=True, assets=compute_avco(fills, held)
    ), False


async def get_cost_basis(
    profile_id: int,
    profile_name: str,
    keys: list[ExchangeKey],
    redis: aioredis.Redis | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> CostBasisResponse:
    """Average buy price per held coin, per exchange, for one profile."""
    cache_key = _cache_key(profile_id)

    memoized = _memo_get(cache_key)
    if memoized is not None:
        return CostBasisResponse(**memoized)
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
        except Exception as exc:  # noqa: BLE001 — cache is best-effort
            _stdlib_logger.warning("Cost-basis cache read failed: %s", exc)
            cached = None
            redis = None
        if cached:
            data = json.loads(cached)
            _memo_set(cache_key, data, COST_BASIS_CACHE_TTL)
            return CostBasisResponse(**data)

    portfolio = await get_portfolio(
        profile_id, profile_name, keys, redis=redis, http_client=http_client
    )
    keys_by_exchange = _dedupe_keys(keys)

    jobs = [
        (ex.exchange, _exchange_cost_basis(keys_by_exchange[ex.exchange], ex.balances, http_client))
        for ex in portfolio.exchanges
        if ex.exchange in keys_by_exchange
    ]
    results = await asyncio.gather(*(job for _, job in jobs), return_exceptions=True)

    exchanges: list[ExchangeCostBasis] = []
    degraded = False
    for (exchange, _), result in zip(jobs, results):
        if isinstance(result, BaseException):
            _stdlib_logger.error("Cost basis failed for %s: %s", exchange, result)
            exchanges.append(ExchangeCostBasis(exchange=exchange, supported=False, assets=[]))
            degraded = True
        else:
            venue, failed = result
            exchanges.append(venue)
            degraded = degraded or failed

    response = CostBasisResponse(
        profile_id=profile_id,
        computed_at=datetime.now(UTC),
        exchanges=exchanges,
    )

    ttl = COST_BASIS_DEGRADED_TTL if degraded else COST_BASIS_CACHE_TTL
    data = json.loads(response.model_dump_json())
    _memo_set(cache_key, data, ttl)
    if redis is not None:
        try:
            await redis.setex(cache_key, ttl, response.model_dump_json())
        except Exception as exc:  # noqa: BLE001
            _stdlib_logger.warning("Cost-basis cache write failed: %s", exc)

    return response
