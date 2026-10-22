"""Forex no layout dashboard: cartão de ligação, gráfico e análises na lateral.

Reaproveita, por herança, o código existente de consulta/validação da API,
start, poll e stop. Este arquivo é apresentação; não inventa preços ou ordens.
"""
import tkinter as tk
from tkinter import ttk

from ds_trader.forex_ui import ForexMarketTab as ForexEngineTab
from ds_trader.forex_live import PAIRS, INTERVALS
from ds_trader.dashboard_shell import label, PANEL, TEXT, MUTED, BORDER, AMBER, GREEN

BG = "#08111f"
HIGHLIGHT = "#0a386e"
RED = "#fb7987"
CYAN = "#4ca9ff"


def card(parent, *, accent=BORDER, padx=16, pady=13):
    return tk.Frame(parent, bg=PANEL, highlightbackground=accent,
                    highlightthickness=1, padx=padx, pady=pady)


class ForexDashboard(ForexEngineTab):
    """Mantém interface pública de ForexMarketTab e motor legado, muda somente view."""

    def __init__(self, parent, root):
        self.root = root
        self.watcher = None
        self.timer = None
        self.running = False
        self.view = None
        self.last_opinion = None
        self.pair = tk.StringVar(value="EUR/USD")
        self.interval = tk.StringVar(value="1min")
        self.refresh = tk.StringVar(value="120")
        self.key = tk.StringVar()
        self.status = tk.StringVar(
            value="DESCONECTADO — insira sua chave de API para receber candles reais.")
        self.next_candle = tk.StringVar(
            value="PROXIMA VELA: AGUARDAR — sem candles recentes")
        self.pattern_notes = tk.StringVar(
            value="Padrões / LTA / LTB: aguardando candles.")
        self.context = tk.StringVar(
            value="Aguardando dados do fornecedor. Nenhuma leitura do mercado atual está disponível.")
        self.prices = tk.StringVar(
            value="Suporte/resistência: aguardando cotações verificadas")
        self.chart_type = "candles"
        self.expanded = False

        base = tk.Frame(parent, bg=BG, padx=13, pady=11)
        base.pack(fill="both", expand=True)
        header = card(base, padx=20, pady=15)
        header.pack(fill="x", pady=(0, 13))
        label(header, "FOREX — CANDLES REAIS DO FORNECEDOR",
              size=14, bold=True).pack(anchor="w")
        label(header,
              "Fonte Twelve Data  •  Candles de 1, 5 ou 15 minutos  •  "
              "Não são ticks nem preços da IQ Option. Chave não é armazenada.",
              size=9, color="#bed3e9", wraplength=1100).pack(anchor="w", pady=(4, 16))

        filters = tk.Frame(header, bg=PANEL)
        filters.pack(fill="x")
        for col, weight in enumerate((3, 2, 2, 4, 3)):
            filters.grid_columnconfigure(col, weight=weight, uniform="forex_filters")
        self.pair_box = self._filter(
            filters, 0, "Par", self.pair, PAIRS, width=13)
        self.interval_box = self._filter(
            filters, 1, "Período", self.interval, list(INTERVALS), width=9)
        self.refresh_box = self._filter(
            filters, 2, "Atualizar (s)", self.refresh, ["120","60","300"], width=8)

        api_holder = tk.Frame(filters, bg=PANEL)
        api_holder.grid(row=0, column=3, sticky="ew", padx=(9, 9))
        label(api_holder, "Chave API", color="#b4cae3", size=9).pack(anchor="w", pady=(0, 6))
        self.key_entry = ttk.Entry(api_holder, textvariable=self.key, show="●")
        self.key_entry.pack(fill="x", ipady=6)
        self.go = tk.Button(
            filters, text="⚡  Conectar ao mercado", command=self.start,
            bg="#0759b9", fg="white", activebackground="#086fe2",
            activeforeground="white", relief="flat", bd=0,
            font=("Segoe UI", 10, "bold"), cursor="hand2",
            highlightbackground="#187ef8", highlightthickness=1,
        )
        self.go.grid(row=0, column=4, sticky="sew", padx=(9, 0), ipady=9)
        self.stop_btn = tk.Button(
            filters, text="■  Desconectar", command=self.stop,
            bg="#253950", fg="white", relief="flat", bd=0, cursor="hand2",
            font=("Segoe UI", 9, "bold"), state="disabled",
        )
        self.stop_btn.grid(row=1, column=4, sticky="ew", padx=(9, 0), pady=(7, 0))
        label(
            header,
            "ⓘ  A API requer sua chave Twelve Data. Consulte limites e custos do plano; "
            "120 s por consulta pode consumir até 720 consultas/dia. Não envie a chave pelo chat.",
            color="#9fbfdf", size=9, wraplength=1160,
        ).pack(anchor="w", pady=(11, 0))

        work = tk.Frame(base, bg=BG)
        work.pack(fill="both", expand=True)
        work.grid_rowconfigure(0, weight=1)
        work.grid_columnconfigure(0, weight=1)
        work.grid_columnconfigure(1, minsize=303)
        left = card(work, padx=15, pady=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 13))
        left_header = tk.Frame(left, bg=PANEL)
        left_header.pack(fill="x", pady=(0, 10))
        self.market_title = label(left_header, "", size=14, bold=True)
        self.market_title.pack(side="left", padx=(1, 10))
        self.interval_badge = label(left_header, "", color="#9ccaf4", bg="#102a46",
                                    size=9, padx=10, pady=5)
        self.interval_badge.pack(side="left")
        self.graph_controls = tk.Frame(left_header, bg=PANEL)
        self.graph_controls.pack(side="right")
        self.candle_btn = self._graph_button(self.graph_controls, "▥", "candles")
        self.line_btn = self._graph_button(self.graph_controls, "⌁", "line")
        self.expand_btn = tk.Button(
            self.graph_controls, text="⛶", command=self.toggle_expand,
            bg="#0b2138", fg="#b5cfe9", relief="flat", bd=0,
            activebackground="#173d67", activeforeground="white",
            font=("Segoe UI", 13), padx=9, pady=3, cursor="hand2",
        )
        self.expand_btn.pack(side="left", padx=2)
        chart_area = tk.Frame(left, bg="#071728", highlightbackground="#19324b",
                              highlightthickness=1)
        chart_area.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(chart_area, bg="#071728", highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _evt: self.draw())

        right = tk.Frame(work, bg=BG, width=303)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_propagate(False)
        self.right = right
        self.signal = card(right, accent="#b56a20", padx=17, pady=16)
        self.signal.pack(fill="x", pady=(0, 12))
        label(self.signal, "◷   PRÓXIMA VELA", color="#dbe9fa",
              bold=True, size=11).pack(anchor="w")
        callout = tk.Frame(self.signal, bg="#302418", padx=13, pady=13)
        callout.pack(fill="x", pady=(14, 0))
        self.side_label = label(callout, "⌛  AGUARDAR", color=AMBER,
                                size=22, bold=True, bg="#302418")
        self.side_label.pack(anchor="center")
        self.side_reason = label(callout, "Sem candles recentes",
                                 color="#ffb962", size=10, bg="#302418",
                                 wraplength=260)
        self.side_reason.pack(anchor="center", pady=(3, 0))

        self.trend_card, self.trend_value, self.trend_details = self._metric(
            right, "▥   Tendência")
        self.lta_card, self.lta_value, self.lta_details = self._metric(
            right, "⌁   LTA / LTB")
        self.zone_card, self.zone_value, self.zone_details = self._metric(
            right, "◇   Suporte / Resistência")

        footer = tk.Frame(base, bg=BG)
        footer.pack(fill="x", pady=(9, 0))
        self.connection_text = label(footer, "", textvariable=self.status,
                                     size=9, color="#efb47f", wraplength=1040)
        self.connection_text.pack(side="left")

        self.status.trace_add("write", lambda *_: self._refresh_cards())
        self.next_candle.trace_add("write", lambda *_: self._refresh_cards())
        self.pattern_notes.trace_add("write", lambda *_: self._refresh_cards())
        self.prices.trace_add("write", lambda *_: self._refresh_cards())
        self.pair.trace_add("write", lambda *_: self._refresh_cards())
        self.interval.trace_add("write", lambda *_: self._refresh_cards())
        self._refresh_cards()
        self.root.after_idle(self.draw)

    def _filter(self, parent, col, title, variable, choices, width):
        holder = tk.Frame(parent, bg=PANEL)
        holder.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 9, 9))
        label(holder, title, color="#b4cae3", size=9).pack(anchor="w", pady=(0, 6))
        box = ttk.Combobox(holder, textvariable=variable, values=choices,
                           state="readonly", width=width)
        box.pack(fill="x", ipady=5)
        return box

    def _graph_button(self, parent, symbol, mode):
        b = tk.Button(
            parent, text=symbol, command=lambda: self.set_chart_type(mode),
            bg="#0c3766" if mode == "candles" else "#0b2138",
            fg="#a7d5ff", activebackground="#12518c",
            activeforeground="white", font=("Segoe UI", 13),
            padx=9, pady=3, relief="flat", bd=0, cursor="hand2"
        )
        b.pack(side="left", padx=2)
        return b

    def _metric(self, parent, title):
        box = card(parent, padx=16, pady=13)
        box.pack(fill="both", expand=True, pady=(0, 12))
        label(box, title, size=10, color="#bfd8f1", bold=True).pack(anchor="w")
        tk.Frame(box, bg="#25415d", height=1).pack(fill="x", pady=(11, 9))
        value = label(box, "Aguardando dados", color="#a3bee0", size=9,
                      wraplength=264)
        value.pack(anchor="w")
        details = label(box, "—     —     —", color="#6797bc", size=9,
                        wraplength=264)
        details.pack(anchor="w", pady=(7, 0))
        return box, value, details

    def _refresh_cards(self):
        # Os cartões nunca apresentam dados fictícios quando a API não conectou.
        self.market_title.configure(text=self.pair.get())
        self.interval_badge.configure(text=self.interval.get().replace("min", " min"))
        active = self.view is not None and self.view.status == "ATUALIZADO"
        opinion = self.last_opinion if active else None
        raw = self.next_candle.get()
        side = "AGUARDAR"
        if active and raw.startswith("PROXIMA VELA: CALL"):
            side = "CALL"
        elif active and raw.startswith("PROXIMA VELA: PUT"):
            side = "PUT"
        tone = GREEN if side == "CALL" else RED if side == "PUT" else AMBER
        self.side_label.configure(text=("↑  " if side == "CALL" else
                                       "↓  " if side == "PUT" else "⌛  ") + side, fg=tone)
        if not active:
            caption = ("Aguardando conexão" if not self.running else
                       "Aguardando candles recentes")
            self.side_reason.configure(text=caption)
            self.trend_value.configure(text="Aguardando dados")
            self.trend_details.configure(text="—     —     —")
            self.lta_value.configure(text="Aguardando dados")
            self.lta_details.configure(text="—     —     —")
            self.zone_value.configure(text="Aguardando dados")
            self.zone_details.configure(text="—     —     —")
            return
        self.side_reason.configure(text="Hipótese educacional · não é entrada na IQ Option"
                                        if side in ("CALL", "PUT") else "Sem confluência ou dados recentes")
        self.trend_value.configure(text=self.view.trend)
        self.trend_details.configure(text=f"Último fechamento UTC: "
                                         f"{self.view.last_closed_at:%H:%M}")
        self.lta_value.configure(text="LTA identificada" if opinion and opinion.lta else
                                 "LTB identificada" if opinion and opinion.ltb else
                                 "Sem linha confirmada")
        self.lta_details.configure(text=self.pattern_notes.get()[:115])
        support = f"{self.view.support:.6f}" if self.view.support is not None else "—"
        resistance = f"{self.view.resistance:.6f}" if self.view.resistance is not None else "—"
        self.zone_value.configure(text=f"S  {support}    R  {resistance}")
        self.zone_details.configure(text="Pivôs confirmados; níveis não garantidos")

    def set_chart_type(self, mode):
        self.chart_type = mode
        self.candle_btn.configure(bg="#0c3766" if mode == "candles" else "#0b2138")
        self.line_btn.configure(bg="#0c3766" if mode == "line" else "#0b2138")
        self.draw()

    def toggle_expand(self):
        if self.expanded:
            self.right.grid()
            self.expanded = False
            self.expand_btn.configure(text="⛶")
        else:
            self.right.grid_remove()
            self.expanded = True
            self.expand_btn.configure(text="◱")
        self.root.after(30, self.draw)

    def draw(self):
        if self.view is None:
            self._empty_chart()
            return
        if self.chart_type == "candles":
            super().draw()
        else:
            self._line_chart()
        self._refresh_cards()

    def _empty_chart(self):
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 120 or h < 120:
            return
        # Grade decorativa e ícone ilustrativo, explicitamente SEM dados.
        for x in range(25, w - 15, max(40, w // 14)):
            c.create_line(x, 10, x, h-25, fill="#10263c", dash=(2, 4))
        for y in range(16, h - 10, max(45, h // 9)):
            c.create_line(20, y, w-17, y, fill="#10263c", dash=(2, 4))
        cx, cy = w / 2, h * .44
        # Símbolo genérico de candles; não são candles de mercado.
        for i, height in enumerate((24, 50, 42, 68, 33, 48, 64)):
            x = cx-80+i*27
            c.create_line(x, cy-height-9, x, cy+18, fill="#183652", width=2)
            c.create_rectangle(x-6, cy-height, x+6, cy-height+25,
                               fill="#1b3652", outline="")
        c.create_text(cx, h*.65,
                      text="Aguardando conexão para exibir candles reais",
                      font=("Segoe UI", 13, "bold"), fill="#b4d6fc")
        c.create_text(cx, h*.65+30,
                      text="Conecte a API da Twelve Data para carregar dados do mercado.",
                      font=("Segoe UI", 10), fill="#83a4c7")

    def _line_chart(self):
        c = self.canvas
        c.delete("all")
        bars = self.view.candles[-75:]
        if not bars:
            return
        w, h = c.winfo_width(), c.winfo_height()
        if w < 160 or h < 120:
            return
        lows = min(b.low for b in bars)
        highs = max(b.high for b in bars)
        span = max(highs-lows, 1e-9)
        low, high = lows-span*.08, highs+span*.08
        def y(p):
            return 15 + (high-p) / (high-low)*(h-48)
        pts=[]
        usable=max(50, w-100)
        for i, b in enumerate(bars):
            x=16+i*usable/max(1,len(bars)-1)
            pts.extend((x,y(b.close)))
        for i in range(5):
            price=low+i*(high-low)/4
            yy=y(price)
            c.create_line(6,yy,w-86,yy,fill="#243c56",dash=(2,4))
            c.create_text(w-43,yy,text=f"{price:.6f}",fill="#bdcedf")
        if len(pts)>=4:
            c.create_line(*pts,fill="#43b7fa",width=2,smooth=False)
        c.create_text(15,h-12,text=bars[0].opened.strftime("%d/%m %H:%M UTC"),
                      fill="#a5bed6",anchor="w")
        c.create_text(w-104,h-12,text=bars[-1].opened.strftime("%H:%M UTC"),
                      fill="#a5bed6",anchor="e")
