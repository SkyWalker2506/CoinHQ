import os
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text

from app.api.v1.router import router as api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")
    # Fail fast if required secrets are missing
    if not settings.JWT_SECRET:
        raise RuntimeError("JWT_SECRET is not set. Application cannot start.")
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY is not set. Application cannot start.")
    app.state.redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    if settings.DEBUG:
        await init_db()
    else:
        # Serverless-safe self-migration (Postgres advisory-locked, best-effort).
        from app.core.migrations import run_startup_migrations
        await run_startup_migrations()
    yield
    # Shutdown
    await app.state.redis.aclose()
    await app.state.http_client.aclose()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-profile crypto portfolio tracker — read-only dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # Our own Vercel frontends (coinhq-*.vercel.app) are always allowed, so a
    # fresh deploy works even before CORS_ORIGINS env is updated.
    allow_origin_regex=r"^https://coinhq-[a-z0-9-]+\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(api_router)


# Public, unauthenticated reachability probe for exchange endpoints. It sends no
# credentials and only ever contacts this fixed allow-list, so it cannot be used
# as an SSRF pivot. Purpose: tell "our code is broken" apart from "the exchange
# blocks this datacenter's region" (Binance answers 451 from US IPs), which is
# otherwise invisible behind a generic 502.
_EXCHANGE_PROBES: dict[str, str] = {
    "binance": "https://api.binance.com/api/v3/ping",
    "binancetr": "https://www.trbinance.com/open/v1/common/time",
    "bybit": "https://api.bybit.com/v5/market/time",
    "okx": "https://www.okx.com/api/v5/public/time",
    "coinbase": "https://api.coinbase.com/v2/time",
    "kraken": "https://api.kraken.com/0/public/Time",
    "gateio": "https://api.gateio.ws/api/v4/spot/time",
}


@app.get("/health/exchanges")
@limiter.limit("6/minute")
async def exchange_reachability(request: Request):
    """Which exchange APIs are reachable from this deployment's region."""
    client: httpx.AsyncClient = request.app.state.http_client
    results: dict[str, dict] = {}

    async def probe(name: str, url: str) -> None:
        try:
            resp = await client.get(url, timeout=8.0)
            results[name] = {
                "status": resp.status_code,
                "reachable": resp.status_code < 400,
                # 451 = geo-blocked for this datacenter, not an app bug
                "note": "geo-blocked from this region" if resp.status_code == 451 else None,
            }
        except Exception as exc:  # noqa: BLE001
            results[name] = {"status": None, "reachable": False, "note": type(exc).__name__}

    import asyncio

    await asyncio.gather(*(probe(n, u) for n, u in _EXCHANGE_PROBES.items()))
    return {
        "region": os.getenv("VERCEL_REGION") or os.getenv("AWS_REGION") or "unknown",
        "exchanges": dict(sorted(results.items())),
    }


@app.get("/health")
async def health(request: Request):
    """Liveness/readiness.

    The database is required — losing it means the app cannot serve. Redis is
    optional (caching + OAuth state have working fallbacks), so an unreachable
    Redis is reported but does NOT fail the check.
    """
    checks: dict = {"status": "ok", "app": settings.APP_NAME, "db": "ok", "redis": "ok"}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        checks["db"] = f"error: {e}"
        checks["status"] = "degraded"

    try:
        await request.app.state.redis.ping()
    except Exception as e:
        checks["redis"] = f"unavailable (running without cache): {e}"

    status_code = 200 if checks["status"] == "ok" else 503
    return JSONResponse(content=checks, status_code=status_code)
