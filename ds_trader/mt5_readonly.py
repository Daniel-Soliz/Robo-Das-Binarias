"""MT5 read-only candle source for DS Trader (experimental, not wired into UI).

The official MetaTrader5 Python package communicates with a local MT5 terminal.
No trading methods are called. This module refuses non-demo accounts.
It never equates broker quotes with IQ Option quotes, including OTC assets.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import importlib
import math
from typing import Callable, Mapping


DEFAULT_SYMBOLS: dict[str, str] = {
    "EUR/USD": "EURUSD",
    "GBP/USD": "GBPUSD",
    "USD/JPY": "USDJPY",
    "USD/CHF": "USDCHF",
    "AUD/USD": "AUDUSD",
    "USD/CAD": "USDCAD",
}


class MT5DataError(RuntimeError):
    """The feed cannot prove the identity, freshness or validity of data."""


@dataclass(frozen=True)
class MT5Bar:
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class MT5Snapshot:
    pair: str
    broker_symbol: str
    interval: str
    candles: tuple[MT5Bar, ...]
    observed_at: datetime
    last_closed_at: datetime
    source: str = "MetaTrader 5 / conta demo (referencia externa)"


class MT5ReadOnlyFeed:
    """Read closed M1 candles from six explicit broker symbols, demo-only.

    Pass a fake mt5 object and a clock in tests. On Windows, the optional
    MetaTrader5 package is imported only when connect() is called. Calling
    initialize() may launch the installed terminal automatically; it does not
    install MT5 or log in to a new account.
    """

    def __init__(self, *, symbols: Mapping[str, str] | None = None,
                 terminal_path: str | None = None, mt5=None,
                 clock: Callable[[], datetime] | None = None):
        self.symbols = dict(DEFAULT_SYMBOLS if symbols is None else symbols)
        if not self.symbols or len(self.symbols) > 6:
            raise ValueError("Configure entre um e seis pares")
        if any(not p or not s or not isinstance(p, str) or not isinstance(s, str)
               for p, s in self.symbols.items()):
            raise ValueError("Mapeamento de simbolos invalido")
        self.terminal_path = terminal_path
        self._mt5 = mt5
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._connected = False

    def connect(self) -> None:
        if self._connected:
            return
        if self._mt5 is None:
            try:
                self._mt5 = importlib.import_module("MetaTrader5")
            except ImportError as exc:
                raise MT5DataError("Instale o pacote MetaTrader5 no Windows") from exc
        mt5 = self._mt5
        # The official MT5 extension documents terminal path as a positional arg.
        if self.terminal_path:
            started = mt5.initialize(self.terminal_path, timeout=60000)
        else:
            started = mt5.initialize(timeout=60000)
        if not started:
            raise MT5DataError("Falha ao iniciar/conectar ao terminal MT5")
        try:
            terminal = mt5.terminal_info()
            account = mt5.account_info()
            if terminal is None or not bool(getattr(terminal, "connected", False)):
                raise MT5DataError("Terminal MT5 sem conexao com o servidor")
            if account is None:
                raise MT5DataError("Conta MT5 nao configurada")
            demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
            if getattr(account, "trade_mode", None) != demo_mode:
                raise MT5DataError("Somente conta DEMO e permitida nesta etapa")
        except Exception:
            mt5.shutdown()
            raise
        self._connected = True

    def close(self) -> None:
        if self._connected:
            self._mt5.shutdown()  # disconnect Python API, not the terminal UI
        self._connected = False

    def read_closed_m1(self, pair: str, *, count: int = 60) -> MT5Snapshot:
        if not self._connected:
            raise MT5DataError("Conecte ao MT5 antes de consultar")
        if pair not in self.symbols:
            raise MT5DataError("Par nao configurado; nao substituir por outro")
        if not 25 <= count <= 240:
            raise ValueError("Solicite entre 25 e 240 candles")
        mt5 = self._mt5
        broker_symbol = self.symbols[pair]
        if mt5.symbol_info(broker_symbol) is None or not mt5.symbol_select(broker_symbol, True):
            raise MT5DataError(f"Simbolo nao disponivel no MT5: {broker_symbol}")
        # Position 0 is the forming candle; position 1 is the most recent closed.
        rows = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_M1, 1, count)
        if rows is None or len(rows) < 25:
            raise MT5DataError("MT5 nao retornou pelo menos 25 candles fechados")
        now = self._clock()
        if now.tzinfo is None:
            raise MT5DataError("Relogio local precisa ter fuso horario")
        now = now.astimezone(timezone.utc)
        bars: list[MT5Bar] = []
        for row in rows:
            try:
                opened = datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)
                op, hi, lo, cl = (float(row[k]) for k in ("open", "high", "low", "close"))
            except (KeyError, ValueError, TypeError, OverflowError, OSError) as exc:
                raise MT5DataError("Candle MT5 incompleto ou invalido") from exc
            if not all(math.isfinite(v) and v > 0 for v in (op, hi, lo, cl)):
                raise MT5DataError("Preco MT5 invalido")
            if lo > min(op, cl) or hi < max(op, cl) or hi < lo:
                raise MT5DataError("OHLC inconsistente")
            bars.append(MT5Bar(opened, op, hi, lo, cl))
        bars.sort(key=lambda b: b.opened_at)
        if len({b.opened_at for b in bars}) != len(bars):
            raise MT5DataError("Candles duplicados")
        if any(b.opened_at.second != 0 for b in bars):
            raise MT5DataError("Abertura M1 nao alinhada ao minuto")
        # 2s buffer avoids treating a just-changing candle as settled.
        if any(b.opened_at + timedelta(seconds=62) > now for b in bars):
            raise MT5DataError("Fechamento da vela ainda nao confirmado")
        age = (now - (bars[-1].opened_at + timedelta(minutes=1))).total_seconds()
        if age > 120:
            raise MT5DataError("Ultimo candle atrasado; AGUARDAR")
        start = len(bars) - 1
        while start > 0 and (bars[start].opened_at - bars[start - 1].opened_at).total_seconds() == 60:
            start -= 1
        contiguous = tuple(bars[start:])
        if len(contiguous) < 25:
            raise MT5DataError("Historico M1 consecutivo insuficiente")
        return MT5Snapshot(pair, broker_symbol, "1min", contiguous, now,
                           contiguous[-1].opened_at + timedelta(minutes=1))
