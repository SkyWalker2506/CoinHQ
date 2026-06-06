from fastapi import APIRouter

from app.api.v1 import admin, auth, keys, portfolio, profiles, share, trade, waitlist

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(profiles.router)
router.include_router(keys.router)
router.include_router(portfolio.router)
router.include_router(share.router)
router.include_router(trade.router)
router.include_router(admin.router)
router.include_router(waitlist.router)
