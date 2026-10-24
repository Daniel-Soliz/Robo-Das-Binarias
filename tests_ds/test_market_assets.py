"""Real-provider contract fixtures, not simulated live prices."""
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
import json

import pytest

from ds_trader.forex_live import (
    AssetSpec, FeedError, classify_market_symbol, fetch_asset_candles,
    parse_asset_payload,
)


SATURDAY = datetime(2026, 10, 24, 12, 37, 15, tzinfo=timezone.utc)


def ohlc(symbol="BTC/USD", interval="1min", start=None):
    start = start or SATURDAY.replace(minute=0, second=0)
    values = []
    for i in range(36):
        price = 70000 + i * 4
        values.append({
            "datetime": (start + timedelta(minutes=i)).strftime("%Y-%m-%d %H:%M:%S"),
            "open": str(price), "high": str(price + 8),
            "low": str(price - 2), "close": str(price + 5),
        })
    return {"status": "ok", "meta": {"symbol": symbol, "interval": interval},
            "values": list(reversed(values))}


def test_crypto_on_saturday_is_not_rejected_by_forex_hours():
    market = parse_asset_payload(ohlc(), AssetSpec("BTC/USD", "CRYPTO"),
                                 "1min", now=SATURDAY)
    assert market.status == "ATUALIZADO"
    assert market.category == "CRYPTO"
    assert market.source == "Twelve Data Crypto"


def test_forex_on_saturday_does_not_claim_current_trade_session():
    view = parse_asset_payload(ohlc(symbol="EUR/USD"),
                               AssetSpec("EUR/USD", "FOREX"), "1min", now=SATURDAY)
    assert "FORA DO HORARIO" in view.status
    assert view.trend == "SEM ANALISE"


def test_classification_rejects_bad_symbol_and_category():
    assert classify_market_symbol("EUR/BRL") == "FOREX"
    assert classify_market_symbol("DOGE/USDT") == "CRYPTO"
    assert classify_market_symbol("NOT A PAIR") is None
    with pytest.raises(ValueError):
        AssetSpec("DOGE/USDT", "FOREX")


def test_crypto_mismatched_symbol_and_duplicate_candles_are_rejected():
    with pytest.raises(FeedError, match="corresponde"):
        parse_asset_payload(ohlc("ETH/USD"), AssetSpec("BTC/USD", "CRYPTO"),
                            "1min", now=SATURDAY)
    payload = ohlc()
    payload["values"].append(dict(payload["values"][0]))
    with pytest.raises(FeedError, match="duplicados"):
        parse_asset_payload(payload, AssetSpec("BTC/USD", "CRYPTO"),
                            "1min", now=SATURDAY)


def test_stale_crypto_does_not_claim_current_opportunity():
    view = parse_asset_payload(ohlc(), AssetSpec("BTC/USD", "CRYPTO"),
                               "1min", now=SATURDAY + timedelta(hours=2))
    assert "ATRASADO" in view.status
    assert view.trend == "SEM ANALISE"


def test_crypto_request_is_read_only_and_key_never_reaches_result_or_error():
    key = "PRIVATE-TWELVE-DATA-KEY"
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_args): return False
        def read(self, _n): return json.dumps(ohlc()).encode()

    def api(request, timeout):
        assert request.get_method() == "GET"
        assert "/time_series?" in request.full_url
        assert timeout == 12
        return Response()

    actual = fetch_asset_candles(key, AssetSpec("BTC/USD", "CRYPTO"),
                                 "1min", opener=api, now=SATURDAY)
    assert actual.category == "CRYPTO"
    assert key not in repr(actual)

    def throttle(request, timeout):
        raise HTTPError(request.full_url, 429, "Rate limited", {}, None)

    with pytest.raises(FeedError) as exc:
        fetch_asset_candles(key, AssetSpec("BTC/USD", "CRYPTO"),
                            "1min", opener=throttle)
    assert key not in str(exc.value)
