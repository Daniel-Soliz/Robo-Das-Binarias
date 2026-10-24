"""Expect the first desktop view to show M5 public-market coverage."""
from types import SimpleNamespace

from ds_trader.dashboard_shell import DashboardShell


def test_dashboard_opens_radar_first():
    shell = DashboardShell.__new__(DashboardShell)
    opened = []
    shell.go = opened.append
    notebook = SimpleNamespace(bind=lambda *args, **kwargs: None)
    shell.mount(notebook, {"radar": object(), "live": object()})
    assert opened == ["radar"]


def test_radar_default_interval_matches_m5():
    from ds_trader.market_radar_ui import DEFAULT_INTERVAL
    assert DEFAULT_INTERVAL == "5min"
