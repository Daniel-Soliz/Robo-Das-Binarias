"""Bounded, provider-backed multiasset watchlist; absolutely no order execution.

Network work never runs on Tkinter's UI thread. Coverage represents each
requested asset explicitly, including errors, stale and unsupported values.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
from typing import Callable, Sequence
import time

from ds_trader.forex_live import (AssetSpec, FeedError, RateLimitError, MarketView,
                                  fetch_asset_candles, INTERVALS)


@dataclass(frozen=True)
class RadarEvent:
    symbol: str
    category: str
    status: str
    snapshot: MarketView | None
    observed_at: datetime
    source: str
    reason: str


@dataclass(frozen=True)
class RadarCoverage:
    requested: int
    current: int
    failed: int
    stale: int
    unsupported: int
    pending: int


class MarketRadar:
    """Poll a bounded set of favorites with per-symbol cadence and backpressure."""

    MAX_FAVORITES = 25

    def __init__(self, api_key: str, specs: Sequence[AssetSpec], *,
                 interval: str = "1min", refresh_seconds: int = 120,
                 query_spacing_seconds: float = 10.0,
                 fetcher: Callable = fetch_asset_candles, utcnow: Callable | None = None,
                 require_key: bool = True):
        if len(specs) > self.MAX_FAVORITES:
            raise ValueError("Selecione no maximo 25 ativos favoritos por vez")
        if len(set(specs)) != len(specs):
            raise ValueError("Ativos favoritos duplicados")
        if not specs or any(not isinstance(spec, AssetSpec) for spec in specs):
            raise ValueError("Escolha ao menos um ativo valido")
        if interval not in INTERVALS or refresh_seconds < 60:
            raise ValueError("Periodo ou frequencia abaixo do limite seguro")
        if not (0.005 <= query_spacing_seconds <= 300):
            raise ValueError("Espacamento das consultas invalido")
        self._key = api_key
        self._require_key = require_key
        self.specs = tuple(specs)
        self.interval = interval
        self.refresh_seconds = refresh_seconds
        self.query_spacing_seconds = query_spacing_seconds
        self._fetcher = fetcher
        self._utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self.events: Queue[RadarEvent] = Queue(maxsize=max(4, len(specs) * 2))
        self._lock = Lock()
        self._states: dict[AssetSpec, RadarEvent | None] = {
            spec: None for spec in self.specs}
        self._stop = Event()
        self._thread: Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def coverage(self, *, now: datetime | None = None) -> RadarCoverage:
        now = now or self._utcnow()
        with self._lock:
            events = tuple(self._states.values())
        states = []
        for event in events:
            if event is None:
                states.append("PENDENTE")
            elif (event.status == "ATUALIZADO" and event.snapshot is not None and
                  (now - event.snapshot.last_closed_at).total_seconds() >
                  max(3 * INTERVALS[self.interval], 180)):
                states.append("ATRASADO")
            else:
                states.append(event.status)
        return RadarCoverage(
            requested=len(self.specs),
            current=states.count("ATUALIZADO"),
            failed=states.count("ERRO"),
            stale=states.count("ATRASADO") + states.count("FORA DO HORARIO"),
            unsupported=states.count("NAO SUPORTADO"),
            pending=states.count("PENDENTE"),
        )

    def start(self):
        if self._require_key and (
                not self._key or len(self._key.strip()) < 6 or
                any(c.isspace() for c in self._key)):
            raise FeedError("Configure sua chave de API no aplicativo para iniciar o radar")
        if self.running:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="ds-market-radar-readonly", daemon=True)
        self._thread.start()

    def stop(self, *, wait=True):
        self._stop.set()
        self._key = ""
        if (wait and self._thread and self._thread.is_alive()):
            self._thread.join(timeout=1)

    def _emit(self, event: RadarEvent):
        if self._stop.is_set():
            return
        try:
            self.events.put_nowait(event)
        except Full:
            try:
                self.events.get_nowait()
            except Empty:
                pass
            try:
                self.events.put_nowait(event)
            except Full:
                pass

    def _run(self):
        due = {spec: 0.0 for spec in self.specs}
        next_global = 0.0
        while not self._stop.is_set():
            now = time.monotonic()
            spec = min(self.specs, key=lambda item: due[item])
            scheduled = max(due[spec], next_global)
            if scheduled > now:
                self._stop.wait(min(.5, scheduled - now))
                continue
            # Do not count this as a quote until a real provider response is parsed.
            observed_at = self._utcnow()
            provider_cooldown = 0.0
            try:
                view = self._fetcher(self._key, spec, self.interval)
                if not isinstance(view, MarketView) or view.pair != spec.symbol or view.category != spec.category:
                    raise FeedError("Metadados do fornecedor nao correspondem ao ativo")
                state = ("ATUALIZADO" if view.status == "ATUALIZADO" else
                         "ATRASADO" if "ATRASADO" in view.status else
                         "FORA DO HORARIO" if "FORA DO HORARIO" in view.status else
                         "ERRO")
                event = RadarEvent(spec.symbol, spec.category, state,
                                   view, observed_at, view.source, view.summary)
            except FeedError as exc:
                message = str(exc)
                if self._key:
                    message = message.replace(self._key, "[credencial omitida]")
                message = message[:250]
                status = ("NAO SUPORTADO" if ("(404)" in message or
                          "nao suportado" in message.lower() or
                          "nao possui fonte" in message.lower()) else "ERRO")
                event = RadarEvent(spec.symbol, spec.category, status, None,
                                   observed_at, ("Twelve Data" if self._key else
                                                 "Kraken/sem fonte"), message)
                if isinstance(exc, RateLimitError):
                    provider_cooldown = max(60, exc.retry_after_seconds or 60)
            except Exception:
                event = RadarEvent(spec.symbol, spec.category, "ERRO", None,
                                   observed_at, "Twelve Data", "Falha de consulta; sem cotacao valida")
            if self._stop.is_set():
                return
            with self._lock:
                self._states[spec] = event
            self._emit(event)
            now = time.monotonic()
            # A rate limit never triggers immediate retry of the same symbol.
            due[spec] = now + (max(60, self.refresh_seconds * 2) if provider_cooldown
                               else self.refresh_seconds)
            next_global = now + max(self.query_spacing_seconds, provider_cooldown)
