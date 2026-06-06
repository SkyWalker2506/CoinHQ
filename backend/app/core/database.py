import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _engine_kwargs() -> dict:
    kwargs: dict = {"echo": settings.DEBUG, "pool_pre_ping": True}
    # Managed Postgres (Supabase) over the public internet: require TLS and disable
    # asyncpg's prepared-statement cache so the URL works through the Supavisor pooler.
    if "supabase." in settings.DATABASE_URL:
        kwargs["connect_args"] = {"ssl": "require", "statement_cache_size": 0}
    # Serverless (Vercel sets VERCEL=1): don't keep a connection pool per function
    # instance — let the external pooler manage connections. Elsewhere use a real pool.
    if os.getenv("VERCEL"):
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20
    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs())

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Use Alembic for migrations in production."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
