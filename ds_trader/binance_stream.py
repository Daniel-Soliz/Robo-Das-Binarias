"""Bounded read-only Binance spot WebSocket worker; never touches Tk."""
from __future__ import annotations

from datetime import datetime, timezone
from queue import Empty, Full, Queue
from threading import Event, Lock, Thread
import json

from ds_trader.binance_public import (BinanceCandleBook, fetch_binance_history,
                                      make_binance_stream_url, WS_SOURCE)
from ds_trader.forex_live import AssetSpec, FeedError, RateLimitError, INTERVALS
from ds_trader.market_radar import RadarCoverage, RadarEvent


class BinanceStreamRadar:
    def __init__(self, specs, *, interval="1min", fetcher=fetch_binance_history,
                 connector=None, utcnow=None, reconnect_seconds=5.0):
        self.specs = tuple(specs)
        self.url = make_binance_stream_url(self.specs, interval)
        if not (0.1 <= reconnect_seconds <= 60):
            raise ValueError("Pausa de reconexao Binance invalida")
        self.interval = interval
        self._fetcher = fetcher
        self._connector = connector
        self._utcnow = utcnow or (lambda: datetime.now(timezone.utc))
        self.reconnect_seconds = reconnect_seconds
        self.events: Queue[RadarEvent] = Queue(maxsize=max(4, len(self.specs) * 2))
        self._lock = Lock()
        self._states: dict[AssetSpec, RadarEvent | None] = {
            spec: None for spec in self.specs}
        self._books = {spec: BinanceCandleBook(spec, interval) for spec in self.specs}
        self._codes = {book.code: spec for spec, book in self._books.items()}
        self._stop = Event()
        self._thread: Thread | None = None

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="ds-binance-spot-public",
                              daemon=True)
        self._thread.start()

    def stop(self, *, wait=True):
        self._stop.set()
        if wait and self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.2)

    def coverage(self, *, now=None):
        now = now or self._utcnow()
        with self._lock:
            values = tuple(self._states.values())
        states = []
        for entry in values:
            if entry is None:
                states.append("PENDENTE")
            elif (entry.status == "ATUALIZADO" and entry.snapshot is not None and
                  (now - entry.snapshot.last_closed_at).total_seconds() >
                  max(180, 3 * INTERVALS[self.interval])):
                states.append("ATRASADO")
            else:
                states.append(entry.status)
        return RadarCoverage(len(self.specs), states.count("ATUALIZADO"),
                             states.count("ERRO"), states.count("ATRASADO"),
                             states.count("NAO SUPORTADO"), states.count("PENDENTE"))

    def drain(self):
        items = []
        while True:
            try:
                items.append(self.events.get_nowait())
            except Empty:
                return tuple(items)

    def _emit(self, event):
        if self._stop.is_set():
            return
        with self._lock:
            self._states[AssetSpec(event.symbol, event.category)] = event
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

    def _error(self, spec, note="Conexao Binance indisponivel; aguardando reconexao"):
        self._emit(RadarEvent(spec.symbol, spec.category, "ERRO", None,
                              self._utcnow(), WS_SOURCE, note))

    def _bootstrap(self):
        for spec in self.specs:
            if self._stop.is_set():
                return False
            try:
                view = self._fetcher(spec, self.interval)
                self._books[spec].seed(view)
                state = "ATUALIZADO" if view.status == "ATUALIZADO" else "ATRASADO"
                self._emit(RadarEvent(spec.symbol, spec.category, state,
                                      view, self._utcnow(), view.source, view.summary))
            except RateLimitError:
                self._error(spec, "Limite de consultas Binance; pausa de 60 segundos")
                return False
            except FeedError as exc:
                message = str(exc).lower()
                if "nao suportado" in message:
                    self._emit(RadarEvent(spec.symbol, spec.category, "NAO SUPORTADO", None,
                                          self._utcnow(), WS_SOURCE,
                                          "Par nao suportado pelo fornecedor Binance"))
                else:
                    self._error(spec, "Historico Binance indisponivel")
            except Exception:
                self._error(spec, "Falha ao obter historico Binance")
        return not self._stop.is_set()

    def _consume(self, raw):
        if not isinstance(raw, str) or len(raw) > 64_000:
            return
        try:
            packet = json.loads(raw)
        except ValueError:
            return
        if not isinstance(packet, dict):
            return
        data = packet.get("data", packet)
        if not isinstance(data, dict):
            return
        spec = self._codes.get(data.get("s"))
        if spec is None:
            return
        try:
            view = self._books[spec].accept(packet, now=self._utcnow())
        except FeedError:
            self._error(spec, "Candle Binance rejeitado; nova sincronizacao necessaria")
            return
        if view is None:
            return
        status = "ATUALIZADO" if view.status == "ATUALIZADO" else "ATRASADO"
        self._emit(RadarEvent(spec.symbol, spec.category, status, view,
                              self._utcnow(), view.source, view.summary))

    def _run(self):
        connector = self._connector
        if connector is None:
            try:
                from websockets.sync.client import connect
                connector = connect
            except ImportError:
                for spec in self.specs:
                    self._error(spec, "Modulo websockets ausente da instalacao")
                return
        retry = self.reconnect_seconds
        while not self._stop.is_set():
            if not self._bootstrap():
                # Provider-wide limit or user stopped: do not retry immediately.
                self._stop.wait(60)
                continue
            try:
                with connector(self.url, open_timeout=8, close_timeout=1,
                               max_size=64_000, max_queue=4, ping_interval=20) as ws:
                    retry = self.reconnect_seconds
                    while not self._stop.is_set():
                        try:
                            frame = ws.recv(timeout=1)
                        except TimeoutError:
                            self._stop.wait(.01)
                            continue
                        self._consume(frame)
            except Exception:
                if self._stop.is_set():
                    return
                for spec in self.specs:
                    self._error(spec)
            self._stop.wait(retry)
            retry = min(60.0, retry * 2)
