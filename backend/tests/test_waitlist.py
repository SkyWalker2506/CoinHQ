"""Tests for api/v1/waitlist.py — waitlist signup endpoint."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import status

from app.api.v1.waitlist import join_waitlist
from app.schemas.waitlist import WaitlistCreate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_waitlist_entry(
    entry_id: int = 1,
    email: str = "test@example.com",
    plan: str | None = "pro",
    source: str | None = "web",
):
    entry = MagicMock()
    entry.id = entry_id
    entry.email = email
    entry.plan = plan
    entry.source = source
    entry.created_at = datetime(2026, 1, 1, 12, 0, 0)
    return entry


def _make_db(existing=None):
    """Return a mock AsyncSession. If `existing` is set, execute returns it."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    db.execute = AsyncMock(return_value=mock_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestWaitlistCreate:
    def test_valid_email_lowercased(self):
        schema = WaitlistCreate(email="  User@Example.COM  ")
        assert schema.email == "user@example.com"

    def test_invalid_email_raises(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            WaitlistCreate(email="not-an-email")

    def test_missing_at_sign_raises(self):
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            WaitlistCreate(email="noatsign.com")

    def test_plan_optional(self):
        schema = WaitlistCreate(email="a@b.com")
        assert schema.plan is None


# ---------------------------------------------------------------------------
# Endpoint unit tests (mocked DB)
# ---------------------------------------------------------------------------

class TestJoinWaitlist:
    @pytest.mark.asyncio
    async def test_new_email_returns_entry(self):
        """New email → entry created, refresh called, ORM object returned."""
        db = _make_db(existing=None)

        async def fake_refresh(obj):
            obj.id = 1
            obj.email = "new@example.com"
            obj.plan = None
            obj.source = "web"
            obj.created_at = datetime(2026, 1, 1)

        db.refresh = AsyncMock(side_effect=fake_refresh)

        payload = WaitlistCreate(email="new@example.com")
        result = await join_waitlist(payload=payload, db=db)

        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_duplicate_email_returns_200_json_response(self):
        """Duplicate email → returns JSONResponse with status 200."""
        existing = _make_waitlist_entry(email="dup@example.com")
        db = _make_db(existing=existing)

        payload = WaitlistCreate(email="dup@example.com")
        response = await join_waitlist(payload=payload, db=db)

        from fastapi.responses import JSONResponse
        assert isinstance(response, JSONResponse)
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_duplicate_no_extra_row(self):
        """Duplicate: db.add is never called — no second row inserted."""
        existing = _make_waitlist_entry(email="dup2@example.com")
        db = _make_db(existing=existing)

        payload = WaitlistCreate(email="dup2@example.com")
        await join_waitlist(payload=payload, db=db)

        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_email_rejected_by_schema(self):
        """Schema raises ValidationError before the handler is even called."""
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            WaitlistCreate(email="bad-email")

    @pytest.mark.asyncio
    async def test_email_normalized_to_lowercase(self):
        """Email is normalized to lowercase before hitting the DB."""
        db = _make_db(existing=None)

        async def fake_refresh(obj):
            obj.id = 2
            obj.email = "upper@example.com"
            obj.plan = None
            obj.source = "web"
            obj.created_at = datetime(2026, 1, 1)

        db.refresh = AsyncMock(side_effect=fake_refresh)

        payload = WaitlistCreate(email="UPPER@EXAMPLE.COM")
        assert payload.email == "upper@example.com"

        await join_waitlist(payload=payload, db=db)
        added_obj = db.add.call_args[0][0]
        assert added_obj.email == "upper@example.com"
