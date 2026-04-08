"""
Market data endpoints — global metrics, coin info, 24h changes.
Powered by CoinMarketCap API (optional, requires CMC_API_KEY).
"""

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.config import settings
from app.services.market_service import get_coin_info, get_global_metrics, get_market_data

router = APIRouter(prefix="/market", tags=["market"])


def _require_cmc() -> None:
    if not settings.CMC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Market data not available — CMC_API_KEY not configured",
        )


@router.get("/global")
async def global_metrics(request: Request):
    """Global crypto market: total market cap, BTC dominance, 24h volume."""
    _require_cmc()
    data = await get_global_metrics(
        http_client=request.app.state.http_client,
        redis_client=request.app.state.redis,
    )
    if not data:
        raise HTTPException(status_code=502, detail="Failed to fetch global metrics")
    return data


@router.get("/listings")
async def market_listings(
    request: Request,
    limit: int = Query(default=100, ge=1, le=200),
):
    """Top N coins with price, 24h/7d change, market cap, volume."""
    _require_cmc()
    data = await get_market_data(
        limit=limit,
        http_client=request.app.state.http_client,
        redis_client=request.app.state.redis,
    )
    if not data:
        raise HTTPException(status_code=502, detail="Failed to fetch market data")
    return data


@router.get("/coin/{symbol}")
async def coin_info(request: Request, symbol: str):
    """Coin metadata: name, description, logo, website, tags."""
    _require_cmc()
    data = await get_coin_info(
        symbols=[symbol.upper()],
        http_client=request.app.state.http_client,
        redis_client=request.app.state.redis,
    )
    if not data or symbol.upper() not in data:
        raise HTTPException(status_code=404, detail=f"Coin info not found for {symbol}")
    return data[symbol.upper()]


@router.get("/coins")
async def coins_info(
    request: Request,
    symbols: str = Query(..., description="Comma-separated symbols, e.g. BTC,ETH,SOL"),
):
    """Batch coin metadata for multiple symbols."""
    _require_cmc()
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        raise HTTPException(status_code=400, detail="No symbols provided")
    if len(symbol_list) > 50:
        raise HTTPException(status_code=400, detail="Max 50 symbols per request")

    data = await get_coin_info(
        symbols=symbol_list,
        http_client=request.app.state.http_client,
        redis_client=request.app.state.redis,
    )
    return data or {}
