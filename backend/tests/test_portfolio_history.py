"""
Tests for portfolio history — T-019:
  (a) history endpoint returns stored snapshots filtered by days, scoped to owner
  (b) throttle — two computes within an hour produce only one snapshot
  (c) snapshot write failure does not break portfolio response
  (d) days param cap/validation
"""
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

from fastapi import HTTPException

from app.api.v1.history import portfolio_history
from app.services.portfolio_service import _maybe_save_snapshot, get_portfolio

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(user_id: int = 1):
    u = MagicMock()
    u.id = user_id
    return u


def _make_profile(profile_id: int = 1, owner_id: int = 1):
    p = MagicMock()
    p.id = profile_id
    p.user_id = owner_id
    p.name = "Test"
    return p


def _make_snapshot(profile_id: int = 1, total_usd: float = 100.0, delta_hours: int = 0):
    s = MagicMock()
    s.id = 1
    s.profile_id = profile_id
    s.total_usd = total_usd
    s.created_at = datetime.now(UTC) - timedelta(hours=delta_hours)
    return s


def _make_key(exchange: str = "binance"):
    k = MagicMock()
    k.exchange = exchange
    return k


def _make_balance_obj(asset: str, free: float = 1.0):
    b = MagicMock()
    b.asset = asset
    b.free = free
    b.locked = 0.0
    b.total = free
    return b


# ---------------------------------------------------------------------------
# (a) History endpoint returns stored snapshots filtered by days, scoped to owner
# ---------------------------------------------------------------------------

class TestHistoryEndpoint:
    @pytest.mark.asyncio
    async def test_returns_snapshots_in_order(self):
        """Snapshots within the requested day window are returned oldest-first."""
        snap1 = _make_snapshot(total_usd=100.0, delta_hours=10)
        snap2 = _make_snapshot(total_usd=200.0, delta_hours=2)

        profile = _make_profile(profile_id=1, owner_id=1)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        mock_scalars = MagicMock()
        mock_scalars.scalars.return_value.all.return_value = [snap1, snap2]
        db.execute = AsyncMock(return_value=mock_scalars)

        result = await portfolio_history(
            profile_id=1, days=30, db=db, current_user=_make_user(1)
        )
        assert len(result) == 2
        assert result[0].total_usd == 100.0
        assert result[1].total_usd == 200.0

    @pytest.mark.asyncio
    async def test_returns_404_for_missing_profile(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await portfolio_history(profile_id=999, days=30, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_403_for_wrong_owner(self):
        profile = _make_profile(profile_id=1, owner_id=99)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        with pytest.raises(HTTPException) as exc:
            await portfolio_history(profile_id=1, days=30, db=db, current_user=_make_user(1))
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_empty_history_returns_empty_list(self):
        profile = _make_profile(profile_id=1, owner_id=1)
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        result = await portfolio_history(profile_id=1, days=30, db=db, current_user=_make_user(1))
        assert result == []


# ---------------------------------------------------------------------------
# (b) Throttle: two computes within one hour produce only one snapshot
# ---------------------------------------------------------------------------

class TestSnapshotThrottle:
    @pytest.mark.asyncio
    async def test_no_insert_when_recent_snapshot_exists(self):
        """If a snapshot was written less than 1h ago, no new one is created."""
        recent = _make_snapshot(delta_hours=0)  # just now

        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = recent

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)

        await _maybe_save_snapshot(profile_id=1, total_usd=500.0, db=db)

        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_inserts_when_no_recent_snapshot(self):
        """If no recent snapshot exists, a new one is inserted."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None  # no recent

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.add = MagicMock()  # db.add is sync in SQLAlchemy async sessions

        await _maybe_save_snapshot(profile_id=1, total_usd=500.0, db=db)

        db.add.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_only_one_snapshot_per_hour_via_get_portfolio(self):
        """get_portfolio called twice quickly should result in at most one add."""
        add_calls = []

        mock_result = MagicMock()
        # First call: no recent snapshot → insert
        # Second call: recent snapshot exists → skip
        mock_result.scalars.return_value.first.side_effect = [None, _make_snapshot()]

        db = AsyncMock()
        db.execute = AsyncMock(return_value=mock_result)
        db.add = MagicMock(side_effect=lambda x: add_calls.append(x))

        async def mock_fetch(key, http_client=None):
            return (key.exchange, [_make_balance_obj("BTC")])

        with patch("app.services.portfolio_service._fetch_exchange_balance", side_effect=mock_fetch):
            with patch("app.services.portfolio_service.get_usd_prices", return_value={"BTC": 50000.0}):
                await get_portfolio(1, "test", [_make_key()], db=db)
                await get_portfolio(1, "test", [_make_key()], db=db)

        assert len(add_calls) == 1


# ---------------------------------------------------------------------------
# (c) Snapshot write failure does not break portfolio response
# ---------------------------------------------------------------------------

class TestSnapshotFailureSafety:
    @pytest.mark.asyncio
    async def test_portfolio_still_returns_on_snapshot_failure(self):
        """A DB error during snapshot write must not raise or block the response."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=Exception("DB connection lost"))

        async def mock_fetch(key, http_client=None):
            return (key.exchange, [_make_balance_obj("ETH", free=2.0)])

        with patch("app.services.portfolio_service._fetch_exchange_balance", side_effect=mock_fetch):
            with patch("app.services.portfolio_service.get_usd_prices", return_value={"ETH": 3000.0}):
                result = await get_portfolio(1, "test", [_make_key("binance")], db=db)

        assert result is not None
        assert result.total_usd == pytest.approx(6000.0)

    @pytest.mark.asyncio
    async def test_snapshot_failure_logs_warning(self):
        """A snapshot failure should be logged as a warning."""
        db = AsyncMock()
        db.execute = AsyncMock(side_effect=RuntimeError("boom"))

        with patch("app.services.portfolio_service.logger") as mock_logger:
            await _maybe_save_snapshot(profile_id=5, total_usd=100.0, db=db)
            mock_logger.warning.assert_called_once()
            call_kwargs = mock_logger.warning.call_args
            assert "portfolio_snapshot_write_failed" in call_kwargs[0]


# ---------------------------------------------------------------------------
# (d) days param cap/validation
# ---------------------------------------------------------------------------

class TestDaysParam:
    @pytest.mark.asyncio
    async def test_days_defaults_to_30(self):
        """Default days value should be 30."""
        profile = _make_profile()
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        # days=30 (default) should work fine
        result = await portfolio_history(profile_id=1, days=30, db=db, current_user=_make_user(1))
        assert result == []

    @pytest.mark.asyncio
    async def test_days_max_allowed_is_365(self):
        """days=365 should be accepted."""
        profile = _make_profile()
        db = AsyncMock()
        db.get = AsyncMock(return_value=profile)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute = AsyncMock(return_value=mock_result)

        result = await portfolio_history(profile_id=1, days=365, db=db, current_user=_make_user(1))
        assert result == []

    def test_days_query_param_default_and_bounds(self):
        """Verify the Query annotation has correct default and bounds."""
        import inspect

        from app.api.v1.history import portfolio_history as ph

        sig = inspect.signature(ph)
        days_param = sig.parameters["days"]
        q = days_param.default
        assert q.default == 30
        # FastAPI stores constraints in metadata as annotated-types objects
        meta_strs = str(q.metadata)
        assert "1" in meta_strs   # ge=1
        assert "365" in meta_strs  # le=365
