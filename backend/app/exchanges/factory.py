from app.exchanges.base import ExchangeAdapter


def get_adapter(exchange: str, api_key: str, api_secret: str) -> ExchangeAdapter:
    """Return the appropriate exchange adapter."""
    exchange = exchange.lower()
    if exchange == "binance":
        from app.exchanges.binance import BinanceAdapter
        return BinanceAdapter(api_key, api_secret)
    elif exchange == "bybit":
        from app.exchanges.bybit import BybitAdapter
        return BybitAdapter(api_key, api_secret)
    elif exchange == "okx":
        from app.exchanges.okx import OKXAdapter
        return OKXAdapter(api_key, api_secret)
    else:
        raise ValueError(f"Unsupported exchange: {exchange}")


SUPPORTED_EXCHANGES = ["binance", "bybit", "okx"]
