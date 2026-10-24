"""M5 history follows the exact screen pair without silently replacing quotes."""
from datetime import datetime, timedelta, timezone
import json

import pytest

from ds_trader.active_source import fetch_active_history
from ds_trader.binance_public import fetch_binance_history
from ds_trader.forex_live import AssetSpec, FeedError, fetch_asset_candles
from ds_trader.public_crypto import parse_kraken_ohlc

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)


def test_source_router_keeps_currency_direction_and_quote_exact():
    calls = []
    def record(provider):
        def fetch(*args, **kwargs):
            calls.append((provider, args, kwargs))
            return provider
        return fetch
    adapters = {"binance_fetcher": record("binance"),
                "kraken_fetcher": record("kraken"),
                "forex_fetcher": record("forex")}
    assert fetch_active_history(AssetSpec("BTC/USDT", "CRYPTO"), api_key="", **adapters) == "binance"
    assert calls[-1] == ("binance", (AssetSpec("BTC/USDT", "CRYPTO"), "5min"),
                         {"history_candles": 288})
    assert fetch_active_history(AssetSpec("BTC/USD", "CRYPTO"), api_key="", **adapters) == "kraken"
    assert calls[-1][1] == ("", AssetSpec("BTC/USD", "CRYPTO"), "5min")
    assert fetch_active_history(AssetSpec("USD/NZD", "FOREX"), api_key="MY_APIKEY", **adapters) == "forex"
    assert calls[-1][1] == ("MY_APIKEY", AssetSpec("USD/NZD", "FOREX"), "5min")
    assert fetch_active_history(AssetSpec("USD/BRL", "FOREX"), api_key="MY_APIKEY", **adapters) == "forex"
    assert calls[-1][1][1].symbol == "USD/BRL"
    with pytest.raises(FeedError, match="chave"):
        fetch_active_history(AssetSpec("USD/JPY", "FOREX"), api_key="", **adapters)


def test_binance_extended_history_requests_289_and_keeps_288_closed():
    spec = AssetSpec("BTC/USDT", "CRYPTO")
    first = NOW - timedelta(minutes=289 * 5)
    rows = []
    for i in range(290):
        ts = int((first + timedelta(minutes=i * 5)).timestamp() * 1000)
        rows.append([ts,"100","110","90","105","1",ts+299999,"1","2"])
    class Reply:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, *_): return json.dumps(rows).encode()
    def opener(request, timeout):
        assert "limit=289" in request.full_url
        assert "interval=5m" in request.full_url
        return Reply()
    snapshot = fetch_binance_history(spec, "5min", history_candles=288,
                                     opener=opener, now=NOW)
    assert len(snapshot.candles) == 288
    assert snapshot.last_closed_at == NOW


def test_kraken_extended_history_removes_open_bar_and_retains_288():
    spec = AssetSpec("ETH/USD", "CRYPTO")
    first = NOW - timedelta(minutes=289 * 5)
    rows = [[int((first+timedelta(minutes=i*5)).timestamp()),"100","110","90","105", "1","2","3"]
            for i in range(290)]
    rows[-1][4] = "INVALID OPEN BAR"
    payload = {"error":[], "result":{"XETHZUSD":rows, "last":123}}
    snapshot = parse_kraken_ohlc(payload, spec, "5min", now=NOW,
                                  history_candles=288)
    assert len(snapshot.candles) == 288
    assert snapshot.last_closed_at == NOW


def test_forex_requests_enough_m5_closed_bars_with_one_optional_key():
    spec = AssetSpec("USD/BRL", "FOREX")
    start = NOW - timedelta(minutes=300 * 5)
    rows = []
    for i in range(300):
        date = start + timedelta(minutes=i * 5)
        rows.append({"datetime":date.strftime("%Y-%m-%d %H:%M:%S"),
                     "open":"5.0","high":"5.2","low":"4.9","close":"5.1"})
    class Reply:
        def __enter__(self):return self
        def __exit__(self, *_):return False
        def read(self, *_):return json.dumps({"status":"ok", "meta":{"symbol":"USD/BRL", "interval":"5min"},
                                              "values":list(reversed(rows))}).encode()
    def opener(request, timeout):
        assert "symbol=USD%2FBRL" in request.full_url
        assert "outputsize=298" in request.full_url
        return Reply()
    snapshot = fetch_asset_candles("KEY-ONLY-IN-MEMORY", spec, "5min",
                                   history_candles=288, opener=opener, now=NOW)
    assert len(snapshot.candles) == 288
    assert snapshot.pair == "USD/BRL"
