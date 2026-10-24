"""App-level auto-discovery contract without requiring a Windows GUI in CI."""
from types import SimpleNamespace
from unittest.mock import patch

from ds_trader.live_modern_ui import LiveScreenTab
from ds_trader.window_capture import IqOptionDiscovery, WindowInfo


def test_iq_option_opening_causes_automatic_monitor_start_after_two_scans():
    tab = LiveScreenTab.__new__(LiveScreenTab)
    tab.active = False
    tab.region = None
    tab._picker = None
    tab._auto_paused = False
    tab._auto_enabled = SimpleNamespace(get=lambda: True)
    tab._auto_guard = IqOptionDiscovery()
    tab._schedule_auto = lambda: None
    tab.status = SimpleNamespace(set=lambda value: None)
    connected = []
    def connect(region, *, window_target):
        tab.region = region
        connected.append((region, window_target))
    tab.selected = connect
    tab.start = lambda: connected.append("started")
    iq = WindowInfo(100, 222, "IQ Option", (20, 30, 1420, 830))
    with patch("ds_trader.live_modern_ui.sys.platform", "win32"), \
         patch("ds_trader.live_modern_ui.enumerate_windows", side_effect=[[], [iq], [iq]]):
        tab._scan_iq_option()
        tab._scan_iq_option()
        assert not connected
        tab._scan_iq_option()
    assert connected[0][1].hwnd == 100
    assert connected[1] == "started"


def test_auto_detection_does_not_override_manual_capture_or_paused_monitor():
    tab = LiveScreenTab.__new__(LiveScreenTab)
    tab.active = False
    tab.region = object()  # the user's explicitly selected region
    tab._picker = None
    tab._auto_paused = False
    tab._auto_enabled = SimpleNamespace(get=lambda: True)
    tab._auto_guard = IqOptionDiscovery()
    tab._schedule_auto = lambda: None
    tab.selected = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("overrode user"))
    tab.start = lambda: (_ for _ in ()).throw(AssertionError("started"))
    with patch("ds_trader.live_modern_ui.sys.platform", "win32"), \
         patch("ds_trader.live_modern_ui.enumerate_windows", side_effect=AssertionError("scanned")):
        tab._scan_iq_option()
        tab.region = None
        tab._auto_paused = True
        tab._scan_iq_option()
