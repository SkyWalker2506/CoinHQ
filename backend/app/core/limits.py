"""
Tier-based feature limits for free and premium users.
"""

TIER_LIMITS: dict[str, dict[str, int]] = {
    "free": {
        "max_profiles": 1,
        "max_exchanges_per_profile": 2,
    },
    "premium": {
        "max_profiles": -1,  # unlimited
        "max_exchanges_per_profile": -1,  # unlimited
    },
}


def check_profile_limit(user, profile_count: int) -> bool:
    """Return True if user is allowed to create another profile."""
    limit = TIER_LIMITS.get(user.tier, TIER_LIMITS["free"])["max_profiles"]
    if limit == -1:
        return True
    return profile_count < limit


def check_exchange_limit(user, exchange_count: int) -> bool:
    """Return True if user is allowed to add another exchange key to a profile."""
    limit = TIER_LIMITS.get(user.tier, TIER_LIMITS["free"])["max_exchanges_per_profile"]
    if limit == -1:
        return True
    return exchange_count < limit
