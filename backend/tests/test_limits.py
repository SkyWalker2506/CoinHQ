"""Tests for core/limits.py — tier-based feature limits."""

from unittest.mock import MagicMock

from app.core.limits import check_exchange_limit, check_profile_limit


def _make_user(tier: str = "free"):
    user = MagicMock()
    user.tier = tier
    return user


class TestCheckProfileLimit:
    def test_free_user_at_limit(self):
        assert check_profile_limit(_make_user("free"), profile_count=1) is False

    def test_free_user_below_limit(self):
        assert check_profile_limit(_make_user("free"), profile_count=0) is True

    def test_premium_user_unlimited(self):
        assert check_profile_limit(_make_user("premium"), profile_count=100) is True

    def test_unknown_tier_defaults_to_free(self):
        assert check_profile_limit(_make_user("nonexistent_tier"), profile_count=1) is False

    def test_admin_defaults_to_free_limits(self):
        """Admin tier is not in TIER_LIMITS, so it defaults to free."""
        assert check_profile_limit(_make_user("admin"), profile_count=1) is False


class TestCheckExchangeLimit:
    def test_free_user_at_limit(self):
        assert check_exchange_limit(_make_user("free"), exchange_count=2) is False

    def test_free_user_below_limit(self):
        assert check_exchange_limit(_make_user("free"), exchange_count=1) is True

    def test_premium_user_unlimited(self):
        assert check_exchange_limit(_make_user("premium"), exchange_count=50) is True

    def test_unknown_tier_defaults_to_free(self):
        assert check_exchange_limit(_make_user("unknown"), exchange_count=2) is False
