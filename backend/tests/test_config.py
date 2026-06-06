"""Tests for core/config.py — DATABASE_URL driver normalization."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from app.core.config import Settings


def _settings(db_url: str) -> Settings:
    return Settings(
        DATABASE_URL=db_url,
        JWT_SECRET="x",
        ENCRYPTION_KEY="y",
    )


def test_plain_postgresql_gets_asyncpg_driver():
    s = _settings("postgresql://u:p@host:5432/db")
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"


def test_heroku_style_postgres_scheme_normalized():
    s = _settings("postgres://u:p@host:5432/db")
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"


def test_already_async_url_unchanged():
    s = _settings("postgresql+asyncpg://u:p@host:5432/db")
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"


def test_libpq_query_params_stripped():
    s = _settings("postgresql://u:p@host:5432/db?sslmode=require")
    assert s.DATABASE_URL == "postgresql+asyncpg://u:p@host:5432/db"


def test_sqlite_url_unchanged():
    s = _settings("sqlite+aiosqlite:///:memory:")
    assert s.DATABASE_URL == "sqlite+aiosqlite:///:memory:"
