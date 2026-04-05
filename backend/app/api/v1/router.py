from fastapi import APIRouter
from app.api.v1 import profiles, keys, portfolio

router = APIRouter(prefix="/api/v1")
router.include_router(profiles.router)
router.include_router(keys.router)
router.include_router(portfolio.router)
