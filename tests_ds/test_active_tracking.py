"""Auto-focus from a verified chart header never reuses the previous pair."""
from datetime import datetime, timedelta, timezone
from threading import Event
import time

from ds_trader.active_tracking import (ActiveAssetTracking, ActiveFocusState,
                                       focus_identity, format_active_focus, retry_delay)
from ds_trader.asset_identity import AssetIdentity, parse_asset_header
from ds_trader.active_history import ActiveHistoryReport
from ds_trader.forex_live import MarketCandle, MarketView, RateLimitError
from tests_ds.test_asset_identity import chart, window_monitor

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
JPY = AssetIdentity("USD/JPY", "M5", False, "FOREX")
BRL = AssetIdentity("USD/BRL", "M5", False, "FOREX")


def eventually(predicate, timeout=1.5):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate(): return
        time.sleep(.01)
    assert predicate()


def report_for(spec):
    return ActiveHistoryReport(spec.symbol, "5min", "Teste fonte Forex", 24, 288,
                               "CALL", "AGUARDAR", "Referencia externa, sem entrada IQ Option")


def snapshot_for(spec):
    opened = NOW - timedelta(minutes=5)
    candle = MarketCandle(opened, 100, 110, 90, 105)
    return MarketView(spec.symbol, "5min", (candle,), NOW, NOW, 0,
                      "ATUALIZADO", "Teste", "ALTA", None, None, "",
                      source="Teste fonte Forex", category=spec.category)


def test_screen_identity_parses_forex_exactly_but_not_unverified_text():
    assert parse_asset_header("USD/JPY M5") == JPY
    assert parse_asset_header("USD / BRL | M5") == BRL
    assert parse_asset_header("USD/NZD M5") == AssetIdentity("USD/NZD", "M5", False, "FOREX")
    assert parse_asset_header("USD BRL") is None


def test_actual_screen_frames_require_three_m5_headers_before_auto_focus():
    monitor = window_monitor()
    for n in (1, 2):
        monitor._process_frame(chart(), header_text="USD/JPY M5", frame_id=n)
        result, _image = monitor.results.get_nowait()
        assert focus_identity(result) is None
    monitor._process_frame(chart(), header_text="USD/JPY M5", frame_id=3)
    result, _image = monitor.results.get_nowait()
    assert focus_identity(result) == JPY
    assert focus_identity(result, selected_timeframe="M1") is None
    assert focus_identity(result, selected_timeframe="M15") is None
    monitor._process_frame(chart(), header_text="USD/NZD M5", frame_id=4)
    changed, _image = monitor.results.get_nowait()
    assert focus_identity(changed) is None


def test_change_of_pair_or_lost_header_invalidates_previous_opinion_immediately():
    tracker = ActiveAssetTracking(fetcher=lambda *_a, **_k: None,
                                  assessor=lambda *_a, **_k: None)
    assert tracker.observe(JPY).symbol == "USD/JPY"
    initial_generation = tracker.generation
    assert tracker.observe(JPY) is None
    changed = tracker.observe(BRL)
    assert changed.generation > initial_generation
    assert changed.symbol == "USD/BRL"
    assert changed.report is None
    cleared = tracker.observe(None)
    assert cleared.report is None
    assert cleared.symbol == ""
    assert cleared.status == "AGUARDAR"


def test_otc_or_wrong_period_blocks_provider_lookup():
    called = []
    tracker = ActiveAssetTracking(fetcher=lambda spec, **_k: called.append(spec))
    otc = AssetIdentity("USD/JPY", "M5", True, "FOREX")
    assert tracker.observe(otc).status == "AGUARDAR"
    assert "OTC" in tracker.drain()[-1].reason
    assert tracker.observe(AssetIdentity("USD/JPY", "M1", False, "FOREX")).status == "AGUARDAR"
    tracker.start()
    try:
        time.sleep(.06)
        assert not called
    finally:
        tracker.stop()


def test_stale_fetch_for_previous_pair_is_suppressed_when_symbol_changes():
    entered, release = Event(), Event()
    requests = []
    def fetch(spec, *, api_key):
        requests.append(spec.symbol)
        if spec.symbol == "USD/JPY":
            entered.set()
            release.wait(2)
        return snapshot_for(spec)
    tracker = ActiveAssetTracking(fetcher=fetch,
                                  assessor=lambda view, **_k: report_for(AssetIdentity(view.pair,"M5",False,"FOREX")),
                                  utcnow=lambda:NOW, refresh_seconds=60)
    tracker.configure_key("ONE-SESSION-KEY")
    tracker.start()
    try:
        tracker.observe(JPY)
        assert entered.wait(1)
        tracker.observe(BRL)
        release.set()
        obtained = []
        def received_brl():
            obtained.extend(tracker.drain())
            return any(s.symbol == "USD/BRL" and s.report is not None for s in obtained)
        eventually(received_brl)
        assert all(s.report is None or s.symbol == "USD/BRL" for s in obtained)
        assert requests[:2] == ["USD/JPY", "USD/BRL"]
        assert obtained[-1].report.operational_side == "AGUARDAR"
    finally:
        release.set()
        tracker.stop()


def test_forex_no_key_reports_source_unavailable_without_network_delay():
    called = []
    tracker = ActiveAssetTracking(fetcher=lambda spec, *, api_key: called.append(spec),
                                  utcnow=lambda:NOW)
    tracker.start()
    try:
        tracker.observe(JPY)
        states=[]
        def got_error():
            states.extend(tracker.drain())
            return any(s.status == "SEM FONTE" for s in states)
        eventually(got_error)
        assert called == []
        assert states[-1].symbol == "USD/JPY"
    finally:
        tracker.stop()


def test_focus_label_separates_external_scenario_from_operational_wait():
    state = ActiveFocusState(5, "USD/BRL", "M5", "CENARIO",
                             "Descricao explicada", report_for(AssetIdentity("USD/BRL","M5",False,"FOREX")))
    text = format_active_focus(state)
    assert "USD/BRL" in text
    assert "M5" in text
    assert "CALL" in text
    assert "AGUARDAR" in text
    assert "IQ Option" in text


def test_focus_scenario_expires_on_local_clock_even_before_network_refresh():
    tracker = ActiveAssetTracking(utcnow=lambda: NOW)
    tracker.observe(JPY)
    state = ActiveFocusState(1, "USD/JPY", "M5", "CENARIO", "Consulta anterior",
                             report_for(JPY), NOW-timedelta(minutes=3))
    tracker._emit(state)
    visible = tracker.current_status(now=NOW)
    assert visible.report is None
    assert visible.status == "AGUARDAR"
    assert "atrasad" in visible.reason.lower()


def test_old_generation_cannot_publish_after_new_identity_even_at_queue_boundary():
    tracker = ActiveAssetTracking(utcnow=lambda:NOW)
    old = tracker.observe(JPY)
    new = tracker.observe(BRL)
    tracker._emit(ActiveFocusState(old.generation, "USD/JPY", "M5", "CENARIO",
                                   "Atrasado", report_for(JPY), NOW))
    current = tracker.current_status(now=NOW)
    assert current.generation == new.generation
    assert current.symbol == "USD/BRL"
    assert current.report is None


def test_provider_rate_limit_honors_retry_window_without_unbounded_delay():
    assert retry_delay(RateLimitError(retry_after_seconds=600), 120) == 600
    assert retry_delay(RateLimitError(retry_after_seconds=7200), 120) == 3600
    assert retry_delay(RateLimitError(retry_after_seconds=20), 120) == 120
