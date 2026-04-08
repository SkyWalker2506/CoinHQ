from fastapi import APIRouter

from app.api.v1 import admin, auth, keys, market, portfolio, profiles, share, trading

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(profiles.router)
router.include_router(keys.router)
router.include_router(portfolio.router)
router.include_router(share.router)
router.include_router(market.router)
router.include_router(trading.router)
router.include_router(admin.router)
