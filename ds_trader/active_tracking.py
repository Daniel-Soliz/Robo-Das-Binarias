"""Follows one confirmed IQ Option chart identity; public history only.

The only signals crossing this thread boundary are immutable, generation-
checked descriptions. Never touches Tk, stores images, or places orders.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
import math
import time

from ds_trader.active_history import ActiveHistoryReport, assess_history
from ds_trader.active_source import fetch_active_history
from ds_trader.asset_identity import AssetIdentity
from ds_trader.forex_live import (AssetSpec, FeedError, RateLimitError,
                                  classify_market_symbol)


@dataclass(frozen=True)
class ActiveFocusState:
    generation: int
    symbol: str
    timeframe: str
    status: str
    reason: str
    report: ActiveHistoryReport | None = None
    last_closed_at: datetime | None = None


def focus_identity(result, *, selected_timeframe: str = "M5") -> AssetIdentity | None:
    """The visual worker is the only authority for which chart is on screen.

    This function is deliberately pure so switching and stale-frame behavior
    can be tested without a Windows/Tk display.
    """
    if (selected_timeframe != "M5" or not result.identity_required or not result.identity_confirmed or
            not result.valid_roi or result.stale_frame or not result.asset):
        return None
    category = classify_market_symbol(result.asset)
    if category is None:
        return None
    return AssetIdentity(result.asset, result.asset_timeframe,
                         result.asset_otc, category)


def retry_delay(error: Exception, normal_seconds: float) -> float:
    """Respect bounded provider cool-downs without faster repeated polling."""
    hint = error.retry_after_seconds if isinstance(error, RateLimitError) else None
    if type(hint) in (int, float) and math.isfinite(hint) and hint > 0:
        return max(normal_seconds, min(3600, hint))
    return normal_seconds


def format_active_focus(state: ActiveFocusState) -> str:
    if state.report is None:
        return f"{state.symbol or 'Sem ativo'} · {state.timeframe or 'M5'} · {state.status}: {state.reason}"
    return (f"{state.symbol} · M5 · CENARIO EXTERNO: {state.report.scenario} "
            f"({state.report.horizon_hours:g}h fechadas, {state.report.source}). "
            f"IQ Option: AGUARDAR. {state.reason}")


class ActiveAssetTracking:
    def __init__(self, *, fetcher=fetch_active_history, assessor=assess_history,
                 utcnow=None, refresh_seconds=120):
        if not 30 <= refresh_seconds <= 3600:
            raise ValueError("Intervalo da consulta ativa invalido")
        self._fetcher = fetcher
        self._assessor = assessor
        self._utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self.refresh_seconds = refresh_seconds
        self._key = ""
        self._observed: AssetIdentity | None = None
        self._target: AssetSpec | None = None
        self._generation = 0
        self._lock = Lock()
        self._stop = Event()
        self._wake = Event()
        self._thread: Thread | None = None
        self.events: Queue[ActiveFocusState] = Queue(maxsize=2)
        self._last_state: ActiveFocusState | None = None

    @property
    def generation(self):
        with self._lock:
            return self._generation

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def _emit(self, state):
        with self._lock:
            # Identity changes and queue publication must be one atomic step:
            # a late HTTP reply must never overwrite the newly selected pair.
            if state.generation != self._generation or self._stop.is_set():
                return
            self._last_state = state
            try:
                self.events.put_nowait(state)
            except Full:
                try:
                    self.events.get_nowait()
                except Empty:
                    pass
                self.events.put_nowait(state)

    def current_status(self, *, now=None):
        """Revoke old external hypotheses immediately, even between HTTP polls."""
        now = now or self._utcnow()
        with self._lock:
            state = self._last_state
        if state is None or state.report is None or state.last_closed_at is None:
            return state
        age = (now - state.last_closed_at).total_seconds()
        if age < 0 or age > 120:
            return replace(state, status="AGUARDAR", report=None,
                           reason="Dados atrasados; cenario externo invalidado ate nova vela fechada")
        return state

    def drain(self):
        results = []
        while True:
            try:
                results.append(self.events.get_nowait())
            except Empty:
                return tuple(results)

    def configure_key(self, key: str):
        key = (key or "").strip()
        with self._lock:
            if key == self._key:
                return
            self._key = key
            self._generation += 1
            generation = self._generation
            observed = self._observed
        if observed is not None:
            self._emit(ActiveFocusState(generation, observed.symbol, observed.timeframe,
                                        "AGUARDAR", "Fonte alterada; aguardando nova consulta"))
        self._wake.set()

    def observe(self, identity: AssetIdentity | None):
        if identity is not None and not isinstance(identity, AssetIdentity):
            identity = None
        with self._lock:
            if self._observed == identity:
                return None
            self._observed = identity
            self._generation += 1
            generation = self._generation
            self._target = None
            reason = "Ativo nao confirmado no grafico; analise anterior invalidada"
            if identity is not None and identity.otc:
                reason = "Ativo OTC: sem historico publico equivalente verificavel"
            elif identity is not None and identity.timeframe != "M5":
                reason = "Periodo do grafico nao e M5; selecione M5 para o modo automatico"
            elif identity is not None:
                try:
                    self._target = AssetSpec(identity.symbol, identity.category)
                    reason = "Par identificado; consultando ate 24h de candles M5 fechados"
                except ValueError:
                    reason = "Identidade do ativo invalida para fonte externa"
            event = ActiveFocusState(generation, identity.symbol if identity else "",
                                     identity.timeframe if identity else "",
                                     "AGUARDAR", reason)
        self._emit(event)
        self._wake.set()
        return event

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="ds-active-market-history", daemon=True)
        self._thread.start()

    def stop(self, *, wait=True):
        self._stop.set()
        self._wake.set()
        with self._lock:
            self._key = ""
            self._generation += 1
            self._target = None
            self._observed = None
            self._last_state = None
        if wait and self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.2)

    def _run(self):
        prior_generation = -1
        next_due = 0.0
        while not self._stop.is_set():
            with self._lock:
                generation = self._generation
                target = self._target
                key = self._key
            if target is None or (generation == prior_generation and
                                  time.monotonic() < next_due):
                self._wake.wait(.5)
                self._wake.clear()
                continue
            prior_generation = generation
            delay = self.refresh_seconds
            try:
                if target.category == "FOREX" and len(key) < 6:
                    raise FeedError("Forex sem chave de fonte intradiaria; configure no Radar")
                view = self._fetcher(target, api_key=key)
                if (view.pair != target.symbol or view.category != target.category or
                        view.interval != "5min"):
                    raise FeedError("Fonte devolveu ativo ou periodo diferente")
                report = self._assessor(view, now=self._utcnow())
                status = "CENARIO" if report.scenario != "AGUARDAR" else "AGUARDAR"
                output = ActiveFocusState(generation, target.symbol, "M5",
                                          status, report.reason, report,
                                          view.last_closed_at)
            except FeedError as exc:
                delay = retry_delay(exc, self.refresh_seconds)
                output = ActiveFocusState(generation, target.symbol, "M5",
                                          "SEM FONTE", str(exc).replace(key, "[chave]") if key
                                          else str(exc))
            except Exception:
                output = ActiveFocusState(generation, target.symbol, "M5", "ERRO",
                                          "Falha de consulta; nenhuma hipotese reutilizada")
            with self._lock:
                valid = self._generation == generation and not self._stop.is_set()
            if valid:
                self._emit(output)
            next_due = time.monotonic() + delay
