"""Tests for exchanges/factory.py — adapter factory."""

import os

os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS0zMi1ieXRlc3h4")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-for-unit-tests-only")

import pytest

from app.exchanges.binance import BinanceAdapter
from app.exchanges.binancetr import BinanceTRAdapter
from app.exchanges.bybit import BybitAdapter
from app.exchanges.coinbase import CoinbaseAdapter
from app.exchanges.factory import SUPPORTED_EXCHANGES, get_adapter
from app.exchanges.kraken import KrakenAdapter
from app.exchanges.okx import OKXAdapter


class TestGetAdapter:
    def test_returns_binance_adapter(self):
        adapter = get_adapter("binance", "key", "secret")
        assert isinstance(adapter, BinanceAdapter)

    def test_returns_bybit_adapter(self):
        adapter = get_adapter("bybit", "key", "secret")
        assert isinstance(adapter, BybitAdapter)

    def test_returns_okx_adapter(self):
        adapter = get_adapter("okx", "key", "secret|passphrase")
        assert isinstance(adapter, OKXAdapter)

    def test_returns_coinbase_adapter(self):
        adapter = get_adapter("coinbase", "key", "secret")
        assert isinstance(adapter, CoinbaseAdapter)

    def test_returns_kraken_adapter(self):
        adapter = get_adapter("kraken", "key", "secret")
        assert isinstance(adapter, KrakenAdapter)

    def test_returns_binancetr_adapter(self):
        adapter = get_adapter("binancetr", "key", "secret")
        assert isinstance(adapter, BinanceTRAdapter)

    def test_case_insensitive(self):
        adapter = get_adapter("BINANCE", "key", "secret")
        assert isinstance(adapter, BinanceAdapter)

    def test_raises_for_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported exchange"):
            get_adapter("unknown_exchange", "key", "secret")

    def test_supported_exchanges_list(self):
        assert set(SUPPORTED_EXCHANGES) == {"binance", "bybit", "okx", "coinbase", "kraken", "binancetr"}
