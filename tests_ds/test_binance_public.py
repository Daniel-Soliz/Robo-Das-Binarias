"""Public Binance spot frames: no auth and never trust an open kline."""
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
import json

import pytest

from ds_trader.forex_live import AssetSpec, FeedError
from ds_trader.binance_public import (BinanceCandleBook, fetch_binance_history,
                                      make_binance_stream_url)

NOW = datetime(2026, 10, 24, 12, 40, tzinfo=timezone.utc)
BTC = AssetSpec("BTC/USDT", "CRYPTO")
ETH = AssetSpec("ETH/USDT", "CRYPTO")


def history():
    start = NOW - timedelta(minutes=36)
    rows = []
    for i in range(37):
        at = int((start + timedelta(minutes=i)).timestamp() * 1000)
        price = 50000 + i * 2
        rows.append([at, str(price), str(price + 5), str(price - 1),
                     str(price + 3), "10", at + 59999, "0", 1, "0", "0", "0"])
    rows[-1][4] = "0.01"  # still-open candle is invalid and must not be inspected
    return rows


def event(*, symbol="BTCUSDT", interval="1m", closed=True, opened=None, price=51000):
    opened = opened or NOW
    start = int(opened.timestamp()*1000)
    return {"stream": "btcusdt@kline_1m", "data": {
        "e": "kline", "E": start+60000, "s": symbol,
        "k": {"t": start, "T": start+59999, "s": symbol, "i": interval,
              "x": closed, "o": str(price), "h": str(price+4),
              "l": str(price-2), "c": str(price+1)}}}


def test_bootstrap_excludes_open_last_bar_and_retains_true_usdt_symbol():
    book = BinanceCandleBook(BTC, "1min")
    view = book.bootstrap(history(), now=NOW)
    assert view.source == "Binance Spot REST público"
    assert view.pair == "BTC/USDT"
    assert view.last_closed_at == NOW
    assert len(view.candles) == 36
    assert all(c.close > 1 for c in view.candles)


def test_closed_kline_event_only_and_out_of_order_is_ignored():
    book = BinanceCandleBook(BTC, "1min")
    book.bootstrap(history(), now=NOW)
    assert book.accept(event(closed=False), now=NOW+timedelta(minutes=1)) is None
    assert book.accept(event(symbol="ETHUSDT"), now=NOW+timedelta(minutes=1)) is None
    assert book.accept(event(interval="5m"), now=NOW+timedelta(minutes=1)) is None
    live = book.accept(event(), now=NOW+timedelta(minutes=1))
    assert live is not None
    assert live.source == "Binance Spot WebSocket público"
    assert live.last_closed_at == NOW+timedelta(minutes=1)
    assert book.accept(event(price=95000), now=NOW+timedelta(minutes=1)) is None
    assert book.accept(event(opened=NOW-timedelta(minutes=2)), now=NOW+timedelta(minutes=1)) is None


def test_bad_price_and_duplicate_or_out_of_order_rest_bars_rejected():
    altered = history()
    altered[3][0] = altered[2][0]
    altered[3][6] = altered[2][6]
    with pytest.raises(FeedError, match="duplicad"):
        BinanceCandleBook(BTC, "1min").bootstrap(altered, now=NOW)
    altered = history()
    altered[4][2] = "not-a-price"
    with pytest.raises(FeedError):
        BinanceCandleBook(BTC, "1min").bootstrap(altered, now=NOW)


def test_gapped_kline_does_not_falsely_claim_long_streak_or_direction():
    book = BinanceCandleBook(BTC, "1min")
    book.bootstrap(history(), now=NOW)
    later = book.accept(event(opened=NOW+timedelta(minutes=3)),
                        now=NOW+timedelta(minutes=4))
    assert later is not None
    assert len(later.candles) == 1
    assert later.trend == "AGUARDANDO"


def test_public_history_get_has_no_key_and_does_not_trade():
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, _): return json.dumps(history()).encode()

    def opener(request, timeout):
        assert request.get_method() == "GET"
        assert request.full_url.startswith("https://data-api.binance.vision/api/v3/klines?")
        assert "symbol=BTCUSDT" in request.full_url
        assert "apiKey" not in request.full_url
        assert timeout == 8
        return Response()

    assert fetch_binance_history(BTC, "1min", opener=opener, now=NOW).pair == "BTC/USDT"
    with pytest.raises(FeedError):
        fetch_binance_history(AssetSpec("BTC/USD", "CRYPTO"), "1min", opener=opener)


def test_closed_event_invalid_ohlc_never_reaches_analysis():
    book = BinanceCandleBook(BTC, "1min")
    book.bootstrap(history(), now=NOW)
    bad = event()
    bad["data"]["k"]["h"] = "3"
    with pytest.raises(FeedError, match="OHLC"):
        book.accept(bad, now=NOW+timedelta(minutes=1))


def test_multiasset_ws_url_is_bounded_and_uses_exact_quote():
    assert make_binance_stream_url((BTC, ETH), "1min") == (
        "wss://data-stream.binance.vision:443/stream?streams="
        "btcusdt@kline_1m/ethusdt@kline_1m")
    with pytest.raises(ValueError):
        make_binance_stream_url(tuple([BTC]*11), "1min")
