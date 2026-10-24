"""Regression tests: OCR text must never silently inherit an old asset."""
from ds_trader.asset_identity import AssetIdentity, IdentityGuard, parse_asset_header
from ds_trader.live_screen import Region, ScreenMonitor
from ds_trader.window_capture import WindowTarget
from PIL import Image, ImageDraw


def chart():
    image = Image.new("RGB", (760, 340), "#101923")
    brush = ImageDraw.Draw(image)
    for i in range(34):
        x = 15 + i * 21
        y = 240 - i * 3
        brush.rectangle((x, y, x + 12, y + 18), fill="#23d18b")
    return image


def window_monitor():
    return ScreenMonitor(Region(0, 0, 760, 340), interval_seconds=.55,
                         window_target=WindowTarget(99, 10, "IQ Option", (0, 0, 900, 600),
                                                    (0, 100, 760, 440)))


def test_forex_header_requires_identifiable_period():
    assert parse_asset_header("IQ Option  EUR/USD (OTC)  M1") == AssetIdentity(
        "EUR/USD", "M1", True, "FOREX"
    )
    assert parse_asset_header("EUR/USD no timeframe") is None


def test_crypto_header_with_usdt_and_m5():
    assert parse_asset_header("BTC / USDT  M5") == AssetIdentity(
        "BTC/USDT", "M5", False, "CRYPTO"
    )


def test_reject_multiple_symbols_and_periods():
    assert parse_asset_header("EUR/USD GBP/USD M1") is None
    assert parse_asset_header("EUR/USD M1 M5") is None
    assert parse_asset_header("IQ OPTION M1") is None


def test_three_consecutive_observations_required_and_switch_resets_immediately():
    guard = IdentityGuard()
    euro = AssetIdentity("EUR/USD", "M1", False, "FOREX")
    pound = AssetIdentity("GBP/USD", "M1", False, "FOREX")
    assert not guard.observe(euro, frame_id=1).confirmed
    assert not guard.observe(euro, frame_id=2).confirmed
    first = guard.observe(euro, frame_id=3)
    assert first.confirmed and first.current == euro

    switched = guard.observe(pound, frame_id=4)
    assert switched.changed
    assert not switched.confirmed
    assert switched.current is None
    assert switched.generation > first.generation
    assert not guard.observe(pound, frame_id=5).confirmed
    last = guard.observe(pound, frame_id=6)
    assert last.confirmed and last.current == pound


def test_missing_or_ambiguous_header_invalidates_old_analysis():
    guard = IdentityGuard()
    euro = AssetIdentity("EUR/USD", "M1", False, "FOREX")
    for n in (1, 2, 3):
        guard.observe(euro, frame_id=n)
    missing = guard.observe(None, frame_id=4)
    assert missing.changed and missing.current is None
    assert not missing.confirmed
    assert guard.observe(None, frame_id=5).generation == missing.generation


def test_late_frame_cannot_restore_previous_asset():
    guard = IdentityGuard()
    euro = AssetIdentity("EUR/USD", "M1", False, "FOREX")
    pound = AssetIdentity("GBP/USD", "M1", False, "FOREX")
    for n in (1, 2, 3):
        guard.observe(euro, frame_id=n)
    newer = guard.observe(pound, frame_id=10)
    late = guard.observe(euro, frame_id=9)
    assert late == newer


def test_monitor_marks_unknown_header_as_unverified():
    monitor = window_monitor()
    monitor._process_frame(chart(), header_text="", frame_id=1)
    result, _ = monitor.results.get_nowait()
    assert not result.identity_confirmed
    assert result.next_visual_bias == "INDEFINIDO"
    assert result.bias == "AGUARDAR"


def test_monitor_switch_flushes_old_visual_outlook_before_confirming_new_asset():
    monitor = window_monitor()
    for i in (1, 2, 3):
        monitor._process_frame(chart(), header_text="EUR/USD M1", frame_id=i)
    euro, _ = monitor.results.get_nowait()
    assert euro.identity_confirmed and euro.asset == "EUR/USD"
    monitor._process_frame(chart(), header_text="BTC/USDT M1", frame_id=4)
    pending, _ = monitor.results.get_nowait()
    assert not pending.identity_confirmed
    assert pending.asset == ""
    assert pending.identity_generation > euro.identity_generation
    assert pending.next_visual_bias == "INDEFINIDO"
    assert pending.bias == "AGUARDAR"


def test_frame_without_its_own_header_cannot_reuse_confirmed_old_asset():
    monitor = window_monitor()
    for i in (1, 2, 3):
        monitor._process_frame(chart(), header_text="EUR/USD M1", frame_id=i)
    assert monitor.results.get_nowait()[0].identity_confirmed
    monitor._process_frame(chart(), header_text=None, frame_id=4)
    pending, _ = monitor.results.get_nowait()
    assert pending.asset == ""
    assert not pending.identity_confirmed
    assert pending.next_visual_bias == "INDEFINIDO"


def test_out_of_order_old_chart_is_discarded_instead_of_published_as_new_asset():
    monitor = window_monitor()
    monitor._process_frame(chart(), header_text="EUR/USD M1", frame_id=11)
    monitor.results.get_nowait()
    monitor._process_frame(chart(), header_text="BTC/USD M1", frame_id=10)
    assert monitor.results.empty()


def test_old_captured_frame_never_restores_current_looking_outlook():
    import time
    monitor = window_monitor()
    for i in (1, 2, 3):
        monitor._process_frame(chart(), header_text="EUR/USD M1", frame_id=i)
    monitor.results.get_nowait()
    monitor._process_frame(chart(), header_text="EUR/USD M1", frame_id=4,
                           captured_at_mono=time.monotonic() - 20)
    result, _ = monitor.results.get_nowait()
    assert result.stale_frame
    assert result.next_visual_bias == "INDEFINIDO"
    assert result.bias == "AGUARDAR"

