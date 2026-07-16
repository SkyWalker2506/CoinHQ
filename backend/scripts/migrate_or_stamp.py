"""Safe migration bootstrap for deploy-time use (idempotent).

Handles the three states a database can be in:
  1. Fresh/empty            → alembic upgrade head (full chain)
  2. Tracked by alembic     → alembic upgrade head (pending revisions only)
  3. Schema exists but no alembic_version (created via init_db/create_all)
                            → stamp the latest pre-existing revision, then
                              upgrade head so only NEW migrations run.

_BASELINE_IF_UNSTAMPED must point at the migration matching the last schema
that could have been created via create_all (currently 010 — waitlist +
snapshots + trade tables all present in models by then).

NOTE: alembic's async env.py calls asyncio.run() itself, so this script stays
synchronous and runs its own inspection queries in separate asyncio.run calls.

Usage (e.g. as a deploy/build step): python scripts/migrate_or_stamp.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402

_BASELINE_IF_UNSTAMPED = "010"

_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))


async def _db_state() -> str:
    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            has_version = await conn.run_sync(
                lambda sc: sc.dialect.has_table(sc, "alembic_version")
            )
            if has_version:
                return "tracked"
            has_users = await conn.run_sync(
                lambda sc: sc.dialect.has_table(sc, "users")
            )
            return "untracked_schema" if has_users else "empty"
    finally:
        await engine.dispose()


async def _sanity() -> None:
    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            if engine.dialect.name == "postgresql":
                res = await conn.execute(text(
                    "SELECT data_type FROM information_schema.columns "
                    "WHERE table_name='share_links' AND column_name='created_at'"
                ))
                print(f"[migrate_or_stamp] share_links.created_at: {res.scalar()}")
    finally:
        await engine.dispose()


def main() -> None:
    state = asyncio.run(_db_state())
    print(f"[migrate_or_stamp] db state: {state}")
    if state == "untracked_schema":
        # Schema predates alembic tracking — align the pointer, then upgrade.
        command.stamp(_cfg, _BASELINE_IF_UNSTAMPED)
        print(f"[migrate_or_stamp] stamped {_BASELINE_IF_UNSTAMPED}")
    command.upgrade(_cfg, "head")
    print("[migrate_or_stamp] upgraded to head")
    asyncio.run(_sanity())


if __name__ == "__main__":
    main()
