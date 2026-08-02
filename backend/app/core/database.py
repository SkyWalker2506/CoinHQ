import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _engine_kwargs() -> dict:
    kwargs: dict = {"echo": settings.DEBUG, "pool_pre_ping": True}
    # Managed Postgres over the public internet (Supabase, Neon, …): require TLS
    # and disable asyncpg's prepared-statement cache, which breaks through
    # transaction poolers (Supavisor, PgBouncer). Local/dev DBs are left alone.
    url = settings.DATABASE_URL
    is_remote_pg = url.startswith("postgresql") and not any(
        h in url for h in ("@localhost", "@127.0.0.1", "@postgres:")
    )
    if is_remote_pg:
        kwargs["connect_args"] = {"ssl": "require", "statement_cache_size": 0}
    # Serverless (Vercel sets VERCEL=1): don't keep a connection pool per function
    # instance — let the external pooler manage connections. Elsewhere use a real pool.
    # SQLite (dev/demo/tests) accepts neither pool_size nor max_overflow.
    if os.getenv("VERCEL"):
        kwargs["poolclass"] = NullPool
    elif settings.DATABASE_URL.startswith("postgresql"):
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
