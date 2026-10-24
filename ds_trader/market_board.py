"""Open our bundled, read-only TradingView market reference in the system browser.

Widgets are visual third-party embeds, never scraped or used for DS Trader signals.
"""
from __future__ import annotations

from pathlib import Path
import sys
import webbrowser


_BUNDLED = Path("ds_trader") / "assets" / "mercados_globais.html"


def market_board_path() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / _BUNDLED
    return Path(__file__).parent / "assets" / "mercados_globais.html"


def open_market_board(*, opener=None) -> bool:
    """Never accept a URL or path from users; the only target is our own file."""
    board = market_board_path()
    if not board.is_file():
        raise FileNotFoundError("Mercados globais: arquivo do painel nao foi incluido na instalacao")
    return bool((opener or webbrowser.open)(board.resolve().as_uri()))
