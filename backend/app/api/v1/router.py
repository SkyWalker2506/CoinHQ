from fastapi import APIRouter

from app.api.v1 import admin, auth, keys, portfolio, profiles, share

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(profiles.router)
router.include_router(keys.router)
router.include_router(portfolio.router)
router.include_router(share.router)
router.include_router(admin.router)
