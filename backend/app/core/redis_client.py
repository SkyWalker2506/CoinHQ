import redis.asyncio as aioredis
from fastapi import Request


def get_redis(request: Request) -> aioredis.Redis:
    """FastAPI dependency — returns the shared Redis client from app.state."""
    return request.app.state.redis
