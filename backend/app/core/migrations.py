"""Startup-time migration bootstrap (Postgres only, race-safe, best-effort).

Serverless platforms often expose secret env vars only at RUNTIME, so build-time
`alembic upgrade` cannot see DATABASE_URL. Instead the app migrates itself on
cold start:

  - Postgres advisory lock ensures exactly one concurrent instance migrates.
  - A schema that predates alembic tracking (created via init_db/create_all)
    is first stamped at _BASELINE_IF_UNSTAMPED, then upgraded, so only newer
    migrations run.
  - Any failure is logged and swallowed — the app still serves traffic.

alembic's async env.py calls asyncio.run(), so the alembic commands run in a
worker thread (asyncio.to_thread) where starting a fresh event loop is legal.
"""

import asyncio
from pathlib import Path

from alembic.config import Config
from sqlalchemy import text

from alembic import command
from app.core.config import settings
from app.core.logging import logger

_BASELINE_IF_UNSTAMPED = "010"
_ADVISORY_LOCK_KEY = 0x0C01_4B1D  # arbitrary app-wide constant

_ALEMBIC_INI = Path(__file__).resolve().parent.parent.parent / "alembic.ini"


def _alembic_cfg() -> Config:
    return Config(str(_ALEMBIC_INI))


def _bootstrap_sync(state: str) -> None:
    cfg = _alembic_cfg()
    if state == "untracked_schema":
        command.stamp(cfg, _BASELINE_IF_UNSTAMPED)
        logger.info("startup_migrations_stamped", revision=_BASELINE_IF_UNSTAMPED)
    command.upgrade(cfg, "head")


async def run_startup_migrations() -> None:
    """Migrate the database to head on startup. Never raises."""
    if not settings.DATABASE_URL.startswith("postgresql"):
        return  # sqlite dev/demo/test environments manage schema explicitly

    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            got = (
                await conn.execute(
                    text("SELECT pg_try_advisory_lock(:k)"), {"k": _ADVISORY_LOCK_KEY}
                )
            ).scalar()
            if not got:
                logger.info("startup_migrations_lock_busy")
                return
            try:
                has_version = await conn.run_sync(
                    lambda sc: sc.dialect.has_table(sc, "alembic_version")
                )
                if has_version:
                    state = "tracked"
                else:
                    has_users = await conn.run_sync(
                        lambda sc: sc.dialect.has_table(sc, "users")
                    )
                    state = "untracked_schema" if has_users else "empty"
                logger.info("startup_migrations_begin", db_state=state)
                await asyncio.to_thread(_bootstrap_sync, state)
                logger.info("startup_migrations_done")
            finally:
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:k)"), {"k": _ADVISORY_LOCK_KEY}
                )
    except Exception as exc:  # noqa: BLE001 — startup must never crash on this
        logger.warning("startup_migrations_skipped", error=str(exc))
