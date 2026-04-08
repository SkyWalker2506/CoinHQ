"""
Trading analysis endpoints — powered by TradingView MCP.
Technical analysis, market screening, backtesting, and global snapshots.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.services.trading_service import (
    ANALYSIS_TTL,
    BACKTEST_TTL,
    SCREENER_TTL,
    SNAPSHOT_TTL,
    VALID_STRATEGIES,
    compare_all_strategies,
    get_coin_analysis,
    get_global_snapshot,
    get_multi_timeframe_analysis,
    get_screener_data,
    run_strategy_backtest,
)

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trading", tags=["trading"])


def _redis(request: Request):
    return getattr(request.app.state, "redis", None)


async def _get_cached(redis_client, key: str) -> dict | list | None:
    if not redis_client:
        return None
    try:
        cached = await redis_client.get(key)
        return json.loads(cached) if cached else None
    except Exception:
        return None


async def _set_cached(redis_client, key: str, data, ttl: int) -> None:
    if not redis_client or not data:
        return
    try:
        await redis_client.setex(key, ttl, json.dumps(data))
    except Exception:
        pass


@router.get("/analysis/{symbol}")
async def coin_analysis(
    request: Request,
    symbol: str,
    exchange: str = Query(default="BINANCE", description="Exchange name"),
    interval: str = Query(
        default="1h",
        description="Timeframe: 1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w, 1M",
    ),
):
    """Full technical analysis for a coin: indicators, RSI, MACD, Bollinger, summary."""
    redis = _redis(request)
    cache_key = f"tv:analysis:{exchange}:{symbol.upper()}:{interval}"

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    try:
        data = await asyncio.to_thread(get_coin_analysis, symbol, exchange, interval=interval)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}") from e

    await _set_cached(redis, cache_key, data, ANALYSIS_TTL)
    return data


@router.get("/analysis/{symbol}/multi")
async def multi_timeframe(
    request: Request,
    symbol: str,
    exchange: str = Query(default="BINANCE"),
):
    """Multi-timeframe analysis (1h, 4h, 1d, 1w) with trend alignment."""
    redis = _redis(request)
    cache_key = f"tv:mtf:{exchange}:{symbol.upper()}"

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    try:
        data = await asyncio.to_thread(get_multi_timeframe_analysis, symbol, exchange)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Multi-TF analysis failed: {e}") from e

    await _set_cached(redis, cache_key, data, ANALYSIS_TTL)
    return data


@router.get("/screener/{exchange}")
async def market_screener(
    request: Request,
    exchange: str,
    limit: int = Query(default=20, ge=1, le=100),
    timeframe: str | None = Query(default=None, description="Optional: 1h, 4h, 1d"),
):
    """Market screener for an exchange — top coins with technical indicators."""
    redis = _redis(request)
    cache_key = f"tv:screener:{exchange.upper()}:{limit}:{timeframe}"

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    try:
        data = await asyncio.to_thread(get_screener_data, exchange, limit, timeframe)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Screener failed: {e}") from e

    await _set_cached(redis, cache_key, data, SCREENER_TTL)
    return data


@router.get("/backtest")
async def backtest(
    request: Request,
    symbol: str = Query(..., description="e.g. BTCUSDT"),
    strategy: str = Query(default="rsi", description=f"One of: {VALID_STRATEGIES}"),
    period: str = Query(default="1y", description="e.g. 1y, 6mo, 3mo"),
    initial_capital: float = Query(default=10000.0, ge=100),
    interval: str = Query(default="1d", description="1d, 4h, 1h"),
):
    """Backtest a trading strategy on a coin."""
    if strategy not in VALID_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Valid: {VALID_STRATEGIES}",
        )

    redis = _redis(request)
    cache_key = f"tv:bt:{symbol}:{strategy}:{period}:{interval}:{initial_capital}"

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    try:
        data = await asyncio.to_thread(
            run_strategy_backtest, symbol, strategy, period, initial_capital, interval
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Backtest failed: {e}") from e

    if "error" in data:
        raise HTTPException(status_code=400, detail=data["error"])

    await _set_cached(redis, cache_key, data, BACKTEST_TTL)
    return data


@router.get("/backtest/compare")
async def backtest_compare(
    request: Request,
    symbol: str = Query(..., description="e.g. BTCUSDT"),
    period: str = Query(default="1y"),
    initial_capital: float = Query(default=10000.0, ge=100),
    interval: str = Query(default="1d"),
):
    """Compare all strategies on a coin."""
    redis = _redis(request)
    cache_key = f"tv:btcmp:{symbol}:{period}:{interval}:{initial_capital}"

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    try:
        data = await asyncio.to_thread(
            compare_all_strategies, symbol, period, initial_capital, interval
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Strategy comparison failed: {e}") from e

    await _set_cached(redis, cache_key, data, BACKTEST_TTL)
    return data


@router.get("/snapshot")
async def market_snapshot(request: Request):
    """Global market snapshot: indices, crypto, forex, commodities."""
    redis = _redis(request)
    cache_key = "tv:snapshot"

    cached = await _get_cached(redis, cache_key)
    if cached:
        return cached

    try:
        data = await asyncio.to_thread(get_global_snapshot)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Snapshot failed: {e}") from e

    await _set_cached(redis, cache_key, data, SNAPSHOT_TTL)
    return data
