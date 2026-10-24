"""Automatic IQ Option discovery is conservative and stays read-only."""
from ds_trader.live_screen import Region
from ds_trader.window_capture import (
    WindowInfo, IqOptionDiscovery, auto_target_for_window,
)


def test_discovers_single_iq_option_window_only_after_stable_observation():
    iq = WindowInfo(15, 200, "IQ Option", (20, 30, 1420, 830))
    other = WindowInfo(16, 201, "DS Trader", (0, 0, 1200, 800))
    finder = IqOptionDiscovery()
    assert finder.observe([other, iq], own_pid=201) is None
    target = finder.observe([other, iq], own_pid=201)
    assert target is not None
    region, window = target
    assert window.hwnd == 15
    assert region == Region(216, 150, 1092, 544)
    assert window.crop == (196, 120, 1288, 664)


def test_ambiguous_windows_and_unrelated_names_cannot_auto_capture():
    finder = IqOptionDiscovery()
    a = WindowInfo(10, 10, "IQ Option", (0, 0, 1200, 700))
    b = WindowInfo(11, 11, "IQ Option - Google Chrome", (0, 0, 1200, 700))
    assert finder.observe([a], own_pid=99) is None
    assert finder.observe([a, b], own_pid=99) is None
    assert finder.observe([b], own_pid=99) is None
    assert finder.observe([b], own_pid=99)[1].hwnd == 11
    assert finder.observe([WindowInfo(12, 12, "Pesquisa sobre IQ Option", (0, 0, 1200, 700))], own_pid=99) is None


def test_small_or_own_window_is_rejected_but_negative_multimonitor_coordinates_work():
    assert auto_target_for_window(WindowInfo(3, 70, "IQ Option", (0, 0, 320, 210))) is None
    assert auto_target_for_window(WindowInfo(3, 70, "IQ Option", (-1400, 0, 0, 900))) is not None
    finder = IqOptionDiscovery()
    own = WindowInfo(3, 70, "IQ Option", (0, 0, 1400, 900))
    assert finder.observe([own], own_pid=70) is None

