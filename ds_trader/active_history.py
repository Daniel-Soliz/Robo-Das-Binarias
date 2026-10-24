"""Conservative M5 historical context, not an IQ Option execution signal."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

from ds_trader.forex_live import INTERVALS, MarketView
from ds_trader.next_candle import evaluate_next


@dataclass(frozen=True)
class ActiveHistoryReport:
    symbol: str
    interval: str
    source: str
    horizon_hours: float
    closed_count: int
    scenario: str  # CALL, PUT, AGUARDAR: only external market context
    operational_side: str  # Always AGUARDAR without broker-side verification
    reason: str


def assess_history(view: MarketView, *, now: datetime) -> ActiveHistoryReport:
    if not isinstance(view, MarketView) or now.tzinfo is None:
        raise ValueError("Historico/horario de analise invalido")
    now = now.astimezone(timezone.utc)
    interval = view.interval
    if interval != "5min":
        raise ValueError("O modo automatico de historico exige M5")
    seconds = INTERVALS[interval]
    maximum = min(288, 24 * 3600 // seconds)
    bars = tuple(view.candles[-maximum:])
    horizon_hours = round(len(bars) * seconds / 3600, 2)

    def wait(why):
        return ActiveHistoryReport(view.pair, interval, view.source, horizon_hours,
                                   len(bars), "AGUARDAR", "AGUARDAR",
                                   f"{view.source}: {why} Referencia externa; "
                                   "nao confirmada na IQ Option.")

    if len(bars) < max(25, 12 * 3600 // seconds):
        return wait("Historico insuficiente: minimo de 12h de candles fechados continuos.")
    if any((bar.opened.tzinfo is None or
            not all(math.isfinite(n) and n > 0 for n in
                    (bar.open, bar.high, bar.low, bar.close)) or
            bar.low > min(bar.open, bar.close) or
            bar.high < max(bar.open, bar.close)) for bar in bars):
        return wait("OHLC invalido na fonte.")
    if any(b.opened - a.opened != timedelta(seconds=seconds)
           for a, b in zip(bars, bars[1:])):
        return wait("Historico com lacuna ou ordem incorreta entre candles.")
    if (bars[-1].opened + timedelta(seconds=seconds) != view.last_closed_at or
            view.last_closed_at > now):
        return wait("Ultimo candle aberto, futuro ou fechamento nao verificavel.")
    elapsed = (now - view.last_closed_at).total_seconds()
    if view.status != "ATUALIZADO" or elapsed > 120:
        return wait("Dados atrasados para hipotese da proxima vela.")
    hypothesis = evaluate_next(bars, source="api", closed_confirmed=True)
    explanatory = "; ".join(hypothesis.reasons[:5])
    return ActiveHistoryReport(
        view.pair, interval, view.source, horizon_hours, len(bars),
        hypothesis.side, "AGUARDAR",
        f"{view.source} · {horizon_hours:g}h de historico real fechado. "
        f"{explanatory} Cenario de referencia externa; falta confirmar "
        "sincronizacao e precos da IQ Option. Nao e sinal operacional.",
    )
