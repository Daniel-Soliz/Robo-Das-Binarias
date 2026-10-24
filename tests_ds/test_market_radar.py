"""Radar tests exercise worker behavior, not pretend to contact market data."""
from datetime import datetime, timedelta, timezone
from threading import Event
import time

import pytest

from ds_trader.forex_live import AssetSpec, FeedError, MarketView, RateLimitError, parse_asset_payload
from ds_trader.market_radar import MarketRadar


FOREX = AssetSpec("EUR/USD", "FOREX")
CRYPTO = AssetSpec("BTC/USD", "CRYPTO")
NOW = datetime.now(timezone.utc)


def snapshot(spec, status="ATUALIZADO"):
    return MarketView(spec.symbol, "1min", (), NOW, NOW, 12, status,
                      "Fechamento reconhecido", "INDEFINIDA", None, None,
                      "Sem nível válido", source="Twelve Data", category=spec.category)


def wait_until(predicate, *, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    assert predicate(), "Radar não atingiu o estado esperado dentro do prazo"


def test_no_key_never_starts_network_request():
    called = []
    radar = MarketRadar("", [FOREX], fetcher=lambda *_: called.append(1))
    with pytest.raises(FeedError):
        radar.start()
    assert called == []


def test_two_assets_are_observed_with_provenance_and_partial_coverage():
    observed = []
    def fetch(key, spec, interval):
        observed.append((spec.symbol, interval))
        return snapshot(spec)
    radar = MarketRadar("test-secret", [FOREX, CRYPTO], refresh_seconds=60,
                        query_spacing_seconds=.01, fetcher=fetch)
    assert radar.coverage().requested == 2
    assert radar.coverage().pending == 2
    try:
        radar.start()
        wait_until(lambda: radar.coverage().current == 2)
        assert set(observed) == {("EUR/USD", "1min"), ("BTC/USD", "1min")}
        events = [radar.events.get_nowait(), radar.events.get_nowait()]
        assert {evt.symbol for evt in events} == {"EUR/USD", "BTC/USD"}
        assert all(evt.snapshot is not None and evt.source == "Twelve Data" for evt in events)
        assert radar.coverage().failed == 0
        assert "test-secret" not in repr(events)
    finally:
        radar.stop()


def test_one_throttled_symbol_does_not_make_partial_scan_look_complete():
    def fetch(key, spec, interval):
        if spec == FOREX:
            raise FeedError("Limite de consultas 429")
        return snapshot(spec)
    radar = MarketRadar("private-key", [FOREX, CRYPTO], refresh_seconds=60,
                        query_spacing_seconds=.01, fetcher=fetch)
    try:
        radar.start()
        wait_until(lambda: radar.coverage().current == 1 and radar.coverage().failed == 1)
        first, second = radar.events.get_nowait(), radar.events.get_nowait()
        errored = first if first.symbol == "EUR/USD" else second
        assert errored.status == "ERRO"
        assert errored.snapshot is None
        assert "private-key" not in errored.reason
    finally:
        radar.stop()


def test_stale_quote_is_separate_from_current_count():
    radar = MarketRadar("private-key", [CRYPTO], refresh_seconds=60,
                        query_spacing_seconds=.01,
                        fetcher=lambda key, spec, interval: snapshot(spec, "ATRASADO"))
    try:
        radar.start()
        wait_until(lambda: radar.coverage().stale == 1)
        assert radar.coverage().current == 0
        assert radar.events.get_nowait().status == "ATRASADO"
    finally:
        radar.stop()


def test_coverage_expires_a_current_quote_without_another_provider_response():
    radar = MarketRadar("private-key", [CRYPTO], refresh_seconds=600,
                        query_spacing_seconds=.01,
                        fetcher=lambda key, spec, interval: snapshot(spec))
    try:
        radar.start()
        wait_until(lambda: radar.coverage().current == 1)
        later = radar.coverage(now=NOW + timedelta(minutes=5))
        assert later.current == 0
        assert later.stale == 1
    finally:
        radar.stop()


def test_stop_during_slow_fetch_does_not_emit_late_result():
    entered = Event()
    release = Event()
    def slow(key, spec, interval):
        entered.set()
        release.wait(2)
        return snapshot(spec)
    radar = MarketRadar("private-key", [FOREX], query_spacing_seconds=.01, fetcher=slow)
    radar.start()
    assert entered.wait(1)
    start = time.monotonic()
    radar.stop(wait=False)
    assert time.monotonic() - start < .1
    release.set()
    wait_until(lambda: not radar.running)
    assert radar.events.empty()


def test_reject_unbounded_universe_instead_of_spending_unknown_credits():
    many = [FOREX] * 26
    with pytest.raises(ValueError, match="favoritos"):
        MarketRadar("valid-key", many)


def test_json_rate_limit_prevents_other_symbols_from_hitting_same_provider():
    requested = []
    attempted = Event()
    def fetch(key, spec, interval):
        requested.append(spec.symbol)
        attempted.set()
        if spec == FOREX:
            return parse_asset_payload({"status": "error", "code": 429}, spec, interval)
        return snapshot(spec)
    radar = MarketRadar("private-key", [FOREX, CRYPTO], query_spacing_seconds=.01,
                        fetcher=fetch)
    try:
        radar.start()
        assert attempted.wait(1)
        time.sleep(.05)
        assert requested == ["EUR/USD"]  # provider-wide cooldown, not only the pair
    finally:
        radar.stop()


def test_test_clock_does_not_depend_on_wall_date():
    radar = MarketRadar("private-key", [CRYPTO], query_spacing_seconds=.01,
                        fetcher=lambda key, spec, interval: snapshot(spec), utcnow=lambda: NOW)
    try:
        radar.start()
        wait_until(lambda: radar.coverage().current == 1)
    finally:
        radar.stop()
