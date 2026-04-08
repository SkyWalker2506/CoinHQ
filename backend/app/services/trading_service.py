"""
Trading analysis service — wraps tradingview-mcp-server for technical analysis,
market screening, backtesting, and market snapshots.

All analysis functions are synchronous (tradingview-mcp uses urllib/requests
internally) and should be called from endpoints via asyncio.to_thread().
"""

import logging
from typing import Any

from tradingview_mcp.core.services.backtest_service import compare_strategies, run_backtest
from tradingview_mcp.core.services.indicators import (
    compute_bb_rating_signal,
    compute_metrics,
    compute_momentum_score,
)
from tradingview_mcp.core.services.screener_provider import fetch_screener_indicators
from tradingview_mcp.core.services.yahoo_finance_service import get_market_snapshot
from tradingview_ta import Interval, TA_Handler

_logger = logging.getLogger(__name__)

INTERVAL_MAP: dict[str, str] = {
    "1m": Interval.INTERVAL_1_MINUTE,
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "30m": Interval.INTERVAL_30_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
    "2h": Interval.INTERVAL_2_HOURS,
    "4h": Interval.INTERVAL_4_HOURS,
    "1d": Interval.INTERVAL_1_DAY,
    "1w": Interval.INTERVAL_1_WEEK,
    "1M": Interval.INTERVAL_1_MONTH,
}

VALID_STRATEGIES = ["rsi", "bollinger", "macd", "ema_crossover", "supertrend", "donchian"]

# Redis cache TTLs (seconds)
ANALYSIS_TTL = 120
SCREENER_TTL = 60
SNAPSHOT_TTL = 300
BACKTEST_TTL = 3600


def get_coin_analysis(
    symbol: str,
    exchange: str = "BINANCE",
    screener: str = "crypto",
    interval: str = "1h",
) -> dict[str, Any]:
    """Full technical analysis for a single coin using TradingView data."""
    ta_interval = INTERVAL_MAP.get(interval, Interval.INTERVAL_1_HOUR)

    handler = TA_Handler(
        symbol=symbol.upper(),
        screener=screener,
        exchange=exchange.upper(),
        interval=ta_interval,
    )
    analysis = handler.get_analysis()

    indicators = analysis.indicators
    summary = analysis.summary

    metrics = compute_metrics(indicators) or {}
    momentum = compute_momentum_score(indicators) or {}
    bb_signal = compute_bb_rating_signal(indicators) or {}

    return {
        "symbol": symbol.upper(),
        "exchange": exchange.upper(),
        "interval": interval,
        "summary": {
            "recommendation": summary.get("RECOMMENDATION", "NEUTRAL"),
            "buy": summary.get("BUY", 0),
            "sell": summary.get("SELL", 0),
            "neutral": summary.get("NEUTRAL", 0),
        },
        "price": {
            "close": indicators.get("close"),
            "open": indicators.get("open"),
            "high": indicators.get("high"),
            "low": indicators.get("low"),
            "volume": indicators.get("volume"),
            "change": indicators.get("change"),
        },
        "indicators": {
            "rsi": indicators.get("RSI"),
            "macd": {
                "macd": indicators.get("MACD.macd"),
                "signal": indicators.get("MACD.signal"),
            },
            "bollinger": {
                "upper": indicators.get("BB.upper"),
                "lower": indicators.get("BB.lower"),
                "basis": indicators.get("BB.basis", indicators.get("SMA20")),
            },
            "ema": {
                "ema10": indicators.get("EMA10"),
                "ema20": indicators.get("EMA20"),
                "ema50": indicators.get("EMA50"),
                "ema100": indicators.get("EMA100"),
                "ema200": indicators.get("EMA200"),
            },
            "sma": {
                "sma10": indicators.get("SMA10"),
                "sma20": indicators.get("SMA20"),
                "sma50": indicators.get("SMA50"),
                "sma200": indicators.get("SMA200"),
            },
            "adx": indicators.get("ADX"),
            "atr": indicators.get("ATR"),
            "stoch_k": indicators.get("Stoch.K"),
            "stoch_d": indicators.get("Stoch.D"),
            "cci": indicators.get("CCI20"),
        },
        "metrics": metrics,
        "momentum": momentum,
        "bb_signal": bb_signal,
    }


def get_multi_timeframe_analysis(
    symbol: str,
    exchange: str = "BINANCE",
    screener: str = "crypto",
) -> dict[str, Any]:
    """Multi-timeframe analysis: 1h, 4h, 1d, 1w."""
    timeframes = ["1h", "4h", "1d", "1w"]
    results: dict[str, dict] = {}

    for tf in timeframes:
        try:
            results[tf] = get_coin_analysis(symbol, exchange, screener, tf)
        except Exception as e:
            _logger.warning("Analysis failed for %s@%s: %s", symbol, tf, e)
            results[tf] = {"error": str(e)}

    recommendations = []
    for tf in timeframes:
        rec = results.get(tf, {}).get("summary", {}).get("recommendation", "")
        if rec:
            recommendations.append(rec)

    buy_count = sum(1 for r in recommendations if "BUY" in r)
    sell_count = sum(1 for r in recommendations if "SELL" in r)
    if buy_count >= 3:
        alignment = "BULLISH"
    elif sell_count >= 3:
        alignment = "BEARISH"
    elif buy_count > sell_count:
        alignment = "SLIGHTLY_BULLISH"
    elif sell_count > buy_count:
        alignment = "SLIGHTLY_BEARISH"
    else:
        alignment = "NEUTRAL"

    return {
        "symbol": symbol.upper(),
        "exchange": exchange.upper(),
        "timeframes": results,
        "alignment": alignment,
    }


def get_screener_data(
    exchange: str = "BINANCE",
    limit: int = 20,
    timeframe: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch screener data for an exchange."""
    return fetch_screener_indicators(
        exchange=exchange.upper(),
        limit=limit,
        timeframe=timeframe,
    )


def run_strategy_backtest(
    symbol: str,
    strategy: str = "rsi",
    period: str = "1y",
    initial_capital: float = 10000.0,
    interval: str = "1d",
) -> dict[str, Any]:
    """Run a backtest for a symbol with a given strategy."""
    if strategy not in VALID_STRATEGIES:
        return {"error": f"Invalid strategy. Valid: {VALID_STRATEGIES}"}

    return run_backtest(
        symbol=symbol,
        strategy=strategy,
        period=period,
        initial_capital=initial_capital,
        interval=interval,
        include_trade_log=True,
        include_equity_curve=False,
    )


def compare_all_strategies(
    symbol: str,
    period: str = "1y",
    initial_capital: float = 10000.0,
    interval: str = "1d",
) -> dict[str, Any]:
    """Compare all strategies for a symbol."""
    return compare_strategies(
        symbol=symbol,
        period=period,
        initial_capital=initial_capital,
        interval=interval,
    )


def get_global_snapshot() -> dict[str, Any]:
    """Global market overview: indices, crypto, commodities, forex."""
    return get_market_snapshot()
