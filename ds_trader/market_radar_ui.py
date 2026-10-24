"""Read-only multiasset radar; network access stays off Tk's main thread."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from tkinter import messagebox, ttk
import tkinter as tk
from queue import Empty

from ds_trader.forex_live import AssetSpec, classify_market_symbol, INTERVALS
from ds_trader.market_radar import MarketRadar, RadarCoverage, RadarEvent
from ds_trader.binance_stream import BinanceStreamRadar
from ds_trader.binance_public import MAX_STREAM_SYMBOLS
from ds_trader.market_board import open_market_board
from ds_trader.public_crypto import fetch_hybrid_market
from ds_trader.theme import BG, PANEL, PANEL_2, TEXT, MUTED, ACCENT


DEFAULT_WATCHLIST = (
    AssetSpec("BTC/USDT", "CRYPTO"), AssetSpec("ETH/USDT", "CRYPTO"),
    AssetSpec("BTC/USD", "CRYPTO"), AssetSpec("ETH/USD", "CRYPTO"),
    AssetSpec("EUR/USD", "FOREX"), AssetSpec("GBP/USD", "FOREX"),
)
DEFAULT_INTERVAL = "5min"


def split_public_sources(specs: tuple[AssetSpec, ...]):
    """Binance USDT candles must never masquerade as a Kraken USD source."""
    streamed = tuple(s for s in specs if s.category == "CRYPTO" and
                     s.symbol.endswith("/USDT"))
    if len(streamed) > MAX_STREAM_SYMBOLS:
        raise ValueError(f"Selecione ate {MAX_STREAM_SYMBOLS} criptomoedas /USDT simultaneas")
    polled = tuple(s for s in specs if s not in streamed)
    return polled, streamed


def combine_coverages(*items: RadarCoverage):
    return RadarCoverage(*(sum(getattr(item, column) for item in items) for column in
                           ("requested", "current", "failed", "stale", "unsupported", "pending")))


def build_market_radar(api_key: str, specs: tuple[AssetSpec, ...], interval: str):
    """With no key, only public Kraken crypto pairs work. Forex stays unavailable."""
    if api_key.strip() and (len(api_key.strip()) < 6 or any(c.isspace() for c in api_key)):
        raise ValueError("A chave Twelve Data informada nao e valida")
    return MarketRadar(api_key, specs, interval=interval,
                       query_spacing_seconds=10.0 if api_key.strip() else 2.0,
                       fetcher=fetch_hybrid_market, require_key=False)


def parse_watchlist(value: str) -> tuple[AssetSpec, ...]:
    """Validate user-selected favorites without assuming source coverage."""
    items = [part.strip().upper().replace(" ", "") for part in value.split(",")]
    if not items or any(not item for item in items) or len(items) > MarketRadar.MAX_FAVORITES:
        raise ValueError("Selecione de 1 a 25 ativos favoritos, separados por virgula")
    if len(set(items)) != len(items):
        raise ValueError("Ativo favorito duplicado")
    specs = []
    for item in items:
        category = classify_market_symbol(item)
        if category is None:
            raise ValueError(f"Ativo invalido: {item}")
        specs.append(AssetSpec(item, category))
    return tuple(specs)


@dataclass(frozen=True)
class RadarRow:
    symbol: str
    category: str
    status: str
    direction: str
    last_closed: str
    source: str
    reason: str


class RadarViewModel:
    """Presentation is based solely on received provider events."""

    def __init__(self, specs=DEFAULT_WATCHLIST):
        self.specs = tuple(specs)
        self._events: dict[str, RadarEvent] = {}

    def apply(self, event: RadarEvent):
        if any(s.symbol == event.symbol and s.category == event.category for s in self.specs):
            self._events[event.symbol] = event

    def disconnect(self):
        self._events.clear()

    def rows(self, *, now: datetime | None = None) -> tuple[RadarRow, ...]:
        now = now or datetime.now(timezone.utc)
        rows = []
        for spec in self.specs:
            event = self._events.get(spec.symbol)
            if event is None:
                rows.append(RadarRow(spec.symbol, spec.category, "SEM FONTE", "—", "—", "—",
                                     "Inicie o radar para consultar a fonte"))
                continue
            available = event.snapshot is not None
            aged_out = (available and
                        (now - event.snapshot.last_closed_at).total_seconds() >
                        max(3 * INTERVALS.get(event.snapshot.interval, 60), 180))
            status = "ATRASADO" if aged_out and event.status == "ATUALIZADO" else event.status
            usable = (status == "ATUALIZADO" and available and
                      event.snapshot.status == "ATUALIZADO")
            direction = (event.snapshot.trend if usable else "—")
            timestamp = (event.snapshot.last_closed_at.strftime("%d/%m %H:%M UTC")
                         if event.snapshot is not None else "—")
            rows.append(RadarRow(spec.symbol, spec.category, status,
                                 direction, timestamp, event.source, event.reason))
        return tuple(rows)


class RadarTab:
    """Minimal Tk UI; all market requests happen inside the radar worker."""

    def __init__(self, parent, root, *, on_update=None):
        self.root = root
        self.on_update = on_update
        self.worker: MarketRadar | None = None
        self.stream_worker: BinanceStreamRadar | None = None
        self.model = RadarViewModel()
        self.key = tk.StringVar()
        self.favorites = tk.StringVar(value=", ".join(s.symbol for s in DEFAULT_WATCHLIST))
        self.interval = tk.StringVar(value=DEFAULT_INTERVAL)
        self.status = tk.StringVar(value="SEM FONTE  ·  Radar desligado")
        self.coverage = tk.StringVar(value=f"0 recebidos · {len(DEFAULT_WATCHLIST)} não consultados")
        self.details = tk.StringVar(value="Selecione um ativo para ver evidências. Sem conexão, não há cotações.")
        self.market_summary = tk.StringVar(value="0 atualizados · 0 altas · 0 baixas")
        self._after_id = None
        self._auto_start_id = None
        self._last_display_rows = ()

        base = tk.Frame(parent, bg=BG, padx=14, pady=11)
        base.pack(fill="both", expand=True)
        head = tk.Frame(base, bg=BG)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="RADAR FOREX + CRIPTO", bg=BG, fg=TEXT,
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(head, textvariable=self.status, bg=PANEL_2, fg="#e9bd78",
                 padx=12, pady=7, font=("Segoe UI", 9, "bold")).pack(side="right")
        tk.Label(base, text="Binance /USDT via WebSocket e Kraken /USD (sem cadastro). "
                      "Forex M1/M5/M15 depende de fonte Twelve Data; separado da IQ Option.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10), anchor="w").pack(fill="x", pady=(0, 12))
        tk.Label(base, text="B3: apenas visualização externa com ~15 min de atraso. Sem análise M1 da B3.",
                 bg=BG, fg="#e9bd78", font=("Segoe UI", 9), anchor="w").pack(
                     fill="x", pady=(0, 8))
        self.board_btn = tk.Button(base, text="↗  Ver B3, Forex e Cripto no TradingView",
                                   command=self.open_markets,
                                   bg=PANEL_2, fg=TEXT, activebackground="#1d4750",
                                   activeforeground=TEXT, relief="flat", bd=0,
                                   padx=15, pady=9, font=("Segoe UI", 10, "bold"),
                                   cursor="hand2")
        self.board_btn.pack(anchor="w", pady=(0, 9))

        tools = tk.Frame(base, bg=PANEL, padx=14, pady=12,
                         highlightbackground="#2b3948", highlightthickness=1)
        tools.pack(fill="x", pady=(0, 12))
        tk.Label(tools, text="CHAVE TWELVE DATA (OPCIONAL)", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 12))
        tk.Label(tools, text="FAVORITOS (até 25)", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=(0, 12))
        tk.Label(tools, text="PERÍODO", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w")
        tools.grid_columnconfigure(1, weight=1)
        ttk.Entry(tools, textvariable=self.key, show="●", width=22).grid(
            row=1, column=0, sticky="ew", padx=(0, 12), pady=(6, 0))
        ttk.Entry(tools, textvariable=self.favorites).grid(
            row=1, column=1, sticky="ew", padx=(0, 12), pady=(6, 0))
        ttk.Combobox(tools, state="readonly", width=8, textvariable=self.interval,
                     values=tuple(INTERVALS)).grid(row=1, column=2, sticky="w", pady=(6, 0))
        self.start_btn = tk.Button(tools, text="Iniciar / atualizar", command=self.start,
                                   bg="#187d91", fg="white", relief="flat", bd=0,
                                   padx=16, pady=8, font=("Segoe UI", 10, "bold"))
        self.start_btn.grid(row=1, column=3, padx=(15, 5), pady=(6, 0))
        self.stop_btn = tk.Button(tools, text="Parar", command=self.stop, bg=PANEL_2,
                                  fg=TEXT, relief="flat", bd=0, padx=10, pady=8,
                                  font=("Segoe UI", 10), state="disabled")
        self.stop_btn.grid(row=1, column=4, pady=(6, 0))
        tk.Label(tools, text="Sem chave: Binance /USDT + Kraken /USD para cripto; Forex sem fonte. "
                      "Com chave: Twelve Data conforme créditos/cobertura do plano.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).grid(
            row=2, column=0, columnspan=5, sticky="w", pady=(10, 0))

        summary_card = tk.Frame(base, bg=PANEL_2, highlightbackground="#23516a",
                                highlightthickness=1, padx=16, pady=10)
        summary_card.pack(fill="x", pady=(0, 10))
        tk.Label(summary_card, text="RADAR M5 · FONTES EXTERNAS", bg=PANEL_2,
                 fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(side="left")
        tk.Label(summary_card, textvariable=self.market_summary, bg=PANEL_2,
                 fg=TEXT, font=("Segoe UI", 10)).pack(side="right")
        table_card = tk.Frame(base, bg=PANEL, padx=12, pady=12,
                              highlightbackground="#2b3948", highlightthickness=1)
        table_card.pack(fill="both", expand=True)
        upper = tk.Frame(table_card, bg=PANEL)
        upper.pack(fill="x", pady=(0, 12))
        tk.Label(upper, text="ATIVOS MONITORADOS", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(upper, textvariable=self.coverage, bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 9)).pack(side="right")
        columns = ("category", "status", "trend", "closed", "source")
        self.table = ttk.Treeview(table_card, columns=columns, show="tree headings", height=9)
        self.table.heading("#0", text="ATIVO")
        self.table.column("#0", width=170, minwidth=110)
        for key, title, width in (
            ("category", "MERCADO", 105), ("status", "ESTADO", 160),
            ("trend", "TENDÊNCIA", 125), ("closed", "ÚLTIMO FECHAMENTO", 185),
            ("source", "FONTE", 135),
        ):
            self.table.heading(key, text=title)
            self.table.column(key, width=width, minwidth=90)
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", self._selected)
        tk.Label(base, textvariable=self.details, bg=BG, fg=MUTED,
                 font=("Segoe UI", 9), anchor="w", justify="left", wraplength=1050).pack(
                 fill="x", pady=(12, 0))
        self._render()
        self._schedule()
        # The request is explicit: public crypto begins without registration.
        # It is background-only, still bounded by provider and rate limits.
        self._auto_start_id = self.root.after(900, self._auto_start)

    def _auto_start(self):
        self._auto_start_id = None
        if self.worker is None and self.stream_worker is None:
            self.start()

    def _schedule(self):
        self._after_id = self.root.after(250, self.poll)

    def _render(self):
        self._last_display_rows = self.model.rows()
        if hasattr(self, "market_summary"):
            rows = self._last_display_rows
            fresh = [row for row in rows if row.status == "ATUALIZADO"]
            up = sum(row.direction == "ALTA" for row in fresh)
            down = sum(row.direction == "BAIXA" for row in fresh)
            self.market_summary.set(f"{len(fresh)} atualizados · {up} altas · {down} baixas · "
                                    f"{len(rows)-len(fresh)} sem cotação atual")
        selected = self.table.selection()
        previous = selected[0] if selected else None
        active = {row.symbol for row in self._last_display_rows}
        for iid in self.table.get_children():
            if iid not in active:
                self.table.delete(iid)
        for row in self._last_display_rows:
            values = (row.category, row.status, row.direction, row.last_closed, row.source)
            if self.table.exists(row.symbol):
                self.table.item(row.symbol, values=values)
            else:
                self.table.insert("", "end", iid=row.symbol, text=row.symbol, values=values)
        if previous and self.table.exists(previous):
            self.table.selection_set(previous)
        elif previous and hasattr(self, "details"):
            self.details.set("Selecione um ativo para ver evidências.")
        if self.on_update:
            self.on_update(self._last_display_rows)

    def _selected(self, _evt=None):
        selected = self.table.selection()
        if not selected:
            return
        row = next((row for row in self.model.rows() if row.symbol == selected[0]), None)
        if row:
            self.details.set(f"{row.symbol} · {row.source} · {row.status}: {row.reason}")

    def open_markets(self):
        try:
            if not open_market_board():
                messagebox.showwarning("Mercados globais", "O navegador nao abriu o painel de mercados.",
                                       parent=self.root)
        except (FileNotFoundError, OSError) as exc:
            messagebox.showwarning("Mercados globais", str(exc), parent=self.root)

    def start(self):
        if ((self.worker is not None and self.worker.running) or
                (self.stream_worker is not None and self.stream_worker.running)):
            return
        radar = None
        stream = None
        try:
            specs = parse_watchlist(self.favorites.get())
            polled, streamed = split_public_sources(specs)
            radar = (build_market_radar(self.key.get(), polled, self.interval.get())
                     if polled else None)
            stream = (BinanceStreamRadar(streamed, interval=self.interval.get())
                      if streamed else None)
            if radar is not None:
                radar.start()
            if stream is not None:
                stream.start()
        except (ValueError, RuntimeError) as exc:
            if radar is not None:
                radar.stop(wait=False)
            if stream is not None:
                stream.stop(wait=False)
            messagebox.showwarning("Radar", str(exc), parent=self.root)
            return
        self.worker = radar
        self.stream_worker = stream
        self.model = RadarViewModel(specs)
        self.status.set("CONSULTANDO · fontes publicas + Twelve Data" if self.key.get().strip()
                        else "CONSULTANDO · fontes publicas, sem chave")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._render()

    def poll(self):
        self._after_id = None
        active = tuple(worker for worker in (self.worker, self.stream_worker) if worker is not None)
        if active:
            received = False
            for radar in active:
                try:
                    while True:
                        event = radar.events.get_nowait()
                        self.model.apply(event)
                        received = True
                except Empty:
                    pass
            coverage = combine_coverages(*(radar.coverage() for radar in active))
            self.coverage.set(f"{coverage.current} atuais · {coverage.failed} falhas · "
                              f"{coverage.stale} atrasados · {coverage.pending} pendentes · "
                              f"{coverage.unsupported} indisponíveis")
            if received or self.model.rows() != self._last_display_rows:
                self._render()
        self._schedule()

    def stop(self):
        if self._auto_start_id is not None:
            self.root.after_cancel(self._auto_start_id)
            self._auto_start_id = None
        if self.worker is not None:
            self.worker.stop(wait=False)
        if self.stream_worker is not None:
            self.stream_worker.stop(wait=False)
        self.worker = None
        self.stream_worker = None
        self.model.disconnect()
        self.key.set("")
        self.status.set("SEM FONTE  ·  Radar desligado")
        self.coverage.set("Nenhuma consulta ativa")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self._render()

    def shutdown(self):
        if self._auto_start_id is not None:
            self.root.after_cancel(self._auto_start_id)
            self._auto_start_id = None
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self.stop()
