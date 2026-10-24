"""Kraken public market candles; no real network calls in this suite."""
import json
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError

import pytest

from ds_trader.forex_live import AssetSpec, FeedError, MarketView
from ds_trader.market_radar import MarketRadar
from ds_trader.public_crypto import (KRAKEN_PAIRS, KRAKEN_RESULT_KEYS,
                                     fetch_public_crypto_candles, parse_kraken_ohlc)


NOW = datetime(2026, 10, 24, 12, 37, tzinfo=timezone.utc)
CRYPTO = AssetSpec("BTC/USD", "CRYPTO")


def kraken_payload():
    first = NOW - timedelta(minutes=37)
    bars = []
    for i in range(38):
        at = first + timedelta(minutes=i)
        price = 72000.0 + i * 9
        bars.append([int(at.timestamp()), str(price), str(price+12),
                     str(price-3), str(price+7), str(price+4), "1.3", 5])
    bars[-1][4] = "1.00"  # deliberately invalid OHLC on OPEN bar only
    return {"error": [], "result": {"XXBTZUSD": bars, "last": 100}}


def test_kraken_excludes_current_uncommitted_candle_even_if_it_has_prices():
    view = parse_kraken_ohlc(kraken_payload(), CRYPTO, "1min", now=NOW)
    assert isinstance(view, MarketView)
    assert view.source == "Kraken Spot público"
    assert view.category == "CRYPTO"
    assert len(view.candles) == 37
    assert view.last_closed_at == NOW
    assert all(bar.close > 100 for bar in view.candles)


def test_kraken_never_labels_candles_of_another_market_as_requested_pair():
    assert set(KRAKEN_PAIRS) == set(KRAKEN_RESULT_KEYS)
    wrong = kraken_payload()
    wrong["result"] = {"XETHZUSD": wrong["result"]["XXBTZUSD"], "last": 100}
    with pytest.raises(FeedError, match="divergente"):
        parse_kraken_ohlc(wrong, CRYPTO, "1min", now=NOW)
    unknown = kraken_payload()
    unknown["result"] = {"TOTALLY_WRONG_MARKET": unknown["result"]["XXBTZUSD"]}
    with pytest.raises(FeedError, match="divergente"):
        parse_kraken_ohlc(unknown, CRYPTO, "1min", now=NOW)


def test_kraken_rejects_duplicate_closed_bars_and_provider_errors():
    duplicate = kraken_payload()
    duplicate["result"]["XXBTZUSD"][-3][0] = duplicate["result"]["XXBTZUSD"][-2][0]
    with pytest.raises(FeedError, match="duplicad"):
        parse_kraken_ohlc(duplicate, CRYPTO, "1min", now=NOW)
    with pytest.raises(FeedError):
        parse_kraken_ohlc({"error": ["EQuery:Unknown asset pair"]}, CRYPTO, "1min", now=NOW)


def test_public_kraken_721_rows_accepts_720_closed_plus_one_open():
    """Live API actually responded with 721 rows on 2026-10-24."""
    bars = []
    for i in range(721):
        stamp = int((NOW - timedelta(minutes=720-i)).timestamp())
        bars.append([stamp, "70000", "70010", "69990", "70005", "70002", "1", 7])
    view = parse_kraken_ohlc({"error": [], "result": {"XXBTZUSD": bars, "last": 1}},
                             CRYPTO, "1min", now=NOW)
    assert len(view.candles) == 120
    assert view.last_closed_at == NOW


def test_public_fetch_has_no_authentication_and_no_open_trade_calls():
    class Response:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self, _): return json.dumps(kraken_payload()).encode()
    def opener(request, timeout):
        assert request.get_method() == "GET"
        assert request.full_url.startswith("https://api.kraken.com/0/public/OHLC?")
        assert "pair=XBTUSD" in request.full_url
        assert "key" not in request.full_url.lower()
        assert "Authorization" not in request.headers
        assert timeout == 8
        return Response()
    result = fetch_public_crypto_candles("", CRYPTO, "1min", now=NOW, opener=opener)
    assert result.pair == "BTC/USD"
    with pytest.raises(FeedError, match="Forex"):
        fetch_public_crypto_candles("", AssetSpec("EUR/USD", "FOREX"), "1min")


def test_rate_limit_error_is_explicit():
    def throttle(req, timeout):
        raise HTTPError(req.full_url, 429, "429", {}, None)
    with pytest.raises(FeedError, match="limite"):
        fetch_public_crypto_candles("", CRYPTO, "1min", opener=throttle)


def test_market_radar_can_run_publicly_without_key_but_not_fake_forex():
    from ds_trader.public_crypto import fetch_hybrid_market
    with pytest.raises(FeedError, match="Forex"):
        fetch_hybrid_market("", AssetSpec("EUR/USD", "FOREX"), "1min")
    radar = MarketRadar("", [CRYPTO], require_key=False,
                        query_spacing_seconds=.01,
                        fetcher=lambda key, spec, interval: parse_kraken_ohlc(
                            kraken_payload(), spec, interval, now=NOW), utcnow=lambda: NOW)
    try:
        radar.start()
        event = radar.events.get(timeout=2)
        assert event.status == "ATUALIZADO"
        assert event.source == "Kraken Spot público"
        assert event.snapshot is not None
    finally:
        radar.stop()


def test_ui_radar_factory_uses_unauthenticated_public_source_by_default():
    from ds_trader.market_radar_ui import build_market_radar
    from ds_trader.public_crypto import fetch_hybrid_market
    radar = build_market_radar("", (CRYPTO,), "1min")
    assert radar._fetcher is fetch_hybrid_market
    assert radar._require_key is False
    assert radar.query_spacing_seconds >= 1
