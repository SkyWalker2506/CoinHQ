"""Trade permission & limit enforcement for delegated (share-link) trading.

Owner trades are not constrained here (the owner controls their own trade key).
Delegated trades placed through a share link are validated against the limits
the owner configured on that link. Withdrawals/transfers are never possible —
trade keys are validated to have withdrawals disabled, and only spot buy/sell
market orders are ever placed.
"""

from app.models.share_link import ShareLink


class TradeNotAllowedError(Exception):
    """Raised when a delegated trade violates the share link's permissions/limits."""


def check_delegate_trade(
    link: ShareLink,
    *,
    side: str,
    base_asset: str,
    usd_value: float,
    spent_today_usd: float,
) -> None:
    """Validate a delegated trade against a share link. Raises TradeNotAllowedError if denied."""
    if not link.can_trade:
        raise TradeNotAllowedError("This share link is not permitted to trade.")

    side = side.lower()
    if side not in ("buy", "sell"):
        raise TradeNotAllowedError("Side must be 'buy' or 'sell'.")

    direction = (link.trade_direction or "both").lower()
    if direction == "buy" and side != "buy":
        raise TradeNotAllowedError("Only buy orders are permitted on this link.")
    if direction == "sell" and side != "sell":
        raise TradeNotAllowedError("Only sell orders are permitted on this link.")

    if link.trade_allowed_coins:
        allowed = {c.strip().upper() for c in link.trade_allowed_coins.split(",") if c.strip()}
        if allowed and base_asset.upper() not in allowed:
            raise TradeNotAllowedError(f"{base_asset.upper()} is not in the allowed coin list.")

    if usd_value <= 0:
        raise TradeNotAllowedError("Order amount must be positive.")

    if link.trade_max_per_order_usd is not None and usd_value > link.trade_max_per_order_usd:
        raise TradeNotAllowedError(
            f"Order exceeds the per-order limit of ${link.trade_max_per_order_usd:,.2f}."
        )

    if (
        link.trade_daily_limit_usd is not None
        and spent_today_usd + usd_value > link.trade_daily_limit_usd
    ):
        raise TradeNotAllowedError(
            f"Order would exceed the 24h limit of ${link.trade_daily_limit_usd:,.2f}."
        )
