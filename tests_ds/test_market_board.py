"""Official visual-only global market board is shipped with the desktop binary."""
from pathlib import Path
import json
import re

import pytest

from ds_trader import market_board


def test_public_board_has_official_widget_b3_delay_and_clear_market_separation():
    board = market_board.market_board_path()
    markup = board.read_text(encoding="utf-8")
    assert "s3.tradingview.com/external-embedding/embed-widget-market-overview.js" in markup
    assert '"BMFBOVESPA:PETR4"' in markup
    assert '"FX:EURUSD"' in markup
    assert '"BINANCE:BTCUSDT"' in markup
    assert "15 minutos" in markup
    assert "TradingView" in markup
    assert "não gera sinais de negociação" in markup
    matched = re.search(r'embed-widget-market-overview\.js" async>\s*(\{.*?\})\s*</script>',
                        markup, re.S)
    assert matched, "A configuracao do widget precisa existir"
    config = json.loads(matched.group(1))
    assert config["colorTheme"] == "dark"
    assert len(config["tabs"]) == 3
    assert all(tab["symbols"] for tab in config["tabs"])


def test_launcher_only_opens_bundled_local_html_uri():
    uris = []
    assert market_board.open_market_board(opener=lambda url: uris.append(url) or True)
    assert uris == [market_board.market_board_path().resolve().as_uri()]


def test_launcher_reports_missing_packaged_asset(monkeypatch, tmp_path):
    monkeypatch.setattr(market_board, "market_board_path", lambda: tmp_path / "missing.html")
    with pytest.raises(FileNotFoundError, match="Mercados globais"):
        market_board.open_market_board(opener=lambda _: True)


def test_packaging_is_relative_to_module_when_not_frozen():
    expected = Path(market_board.__file__).parent / "assets" / "mercados_globais.html"
    assert market_board.market_board_path() == expected


def test_packaging_looks_up_assets_inside_pyinstaller_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(market_board.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert market_board.market_board_path() == (tmp_path / "ds_trader" / "assets" /
                                                "mercados_globais.html")
