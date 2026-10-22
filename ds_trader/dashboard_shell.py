"""Estrutura visual única do DS Trader: navegação lateral, cabeçalho e rodapé.

Não contém lógica financeira nem captura dados. As páginas existentes ficam
na mesma instância de ttk.Notebook para preservar seus estados e testes.
"""
import tkinter as tk
from tkinter import ttk
from ds_trader.theme import BG, PANEL, PANEL_2, TEXT, MUTED, ACCENT

HEADER = "#071728"
BORDER = "#1d3650"
BLUE = "#0b4b9b"
GREEN = "#48d39f"
AMBER = "#ffc16c"

NAV_ITEMS = (
    ("overview", "⌂", "Visão geral"),
    ("chart", "⌁", "Gráfico e reprodução"),
    ("forex", "◎", "Forex em tempo real"),
    ("live", "▣", "Tela ao vivo"),
    ("events", "▥", "Sinais e histórico"),
    ("reports", "♜", "Resultados"),
    ("config", "⚙", "Configurações"),
    ("help", "?", "Ajuda"),
)


def label(parent, text, *, size=10, color=TEXT, bold=False, bg=None, **kwargs):
    return tk.Label(
        parent, text=text, bg=bg or parent.cget("bg"), fg=color,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        anchor="w", justify="left", **kwargs
    )


class DashboardShell:
    def __init__(self, root, actions):
        self.root = root
        root.configure(bg=BG)
        root.geometry("1510x925")
        root.minsize(1130, 740)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # Sempre preservar ações originais de importação, demo e relatórios.
        self.header = tk.Frame(root, bg=HEADER, height=91,
                               highlightbackground=BORDER, highlightthickness=1)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)

        brand = tk.Frame(self.header, bg=HEADER)
        brand.pack(side="left", padx=(28, 14), pady=13)
        tk.Label(brand, text="◈", bg=HEADER, fg="#19b8ff",
                 font=("Segoe UI Symbol", 31, "bold")).pack(side="left", padx=(0, 14))
        label(brand, "DS Trader", size=21, bold=True, bg=HEADER).pack(side="left")
        tk.Frame(self.header, width=1, height=33, bg="#35516a").pack(side="left")
        label(self.header, "ANÁLISE E SIMULAÇÃO   •   SEM ORDENS REAIS",
              size=9, color="#6fa5df", bg=HEADER, bold=True).pack(
                  side="left", padx=(20, 10))

        actions_box = tk.Frame(self.header, bg=HEADER)
        actions_box.pack(side="right", padx=18)
        for title, command, glyph in reversed(actions):
            button = tk.Button(
                actions_box, text=f"{glyph}  {title}", command=command,
                bg="#0b2038", fg="#e7f3ff", activebackground="#143958",
                activeforeground="white", padx=13, pady=10, relief="flat",
                borderwidth=0, highlightthickness=1, highlightbackground="#27435e",
                font=("Segoe UI", 9, "normal"), cursor="hand2"
            )
            button.pack(side="right", padx=5)

        stage = tk.Frame(root, bg=BG)
        stage.grid(row=1, column=0, sticky="nsew")
        stage.grid_rowconfigure(0, weight=1)
        stage.grid_columnconfigure(1, weight=1)
        self.sidebar = tk.Frame(stage, bg="#07192b", width=224)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        tk.Frame(stage, width=1, bg=BORDER).grid(row=0, column=0, sticky="nse")
        self.content = tk.Frame(stage, bg=BG)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.nav_buttons = {}
        self.nav_frames = {}
        self.current = None

        space = tk.Frame(self.sidebar, bg="#07192b", height=18)
        space.pack(fill="x")
        for name, symbol, title in NAV_ITEMS:
            item = tk.Frame(self.sidebar, bg="#07192b", height=53)
            item.pack(fill="x", padx=(12, 8), pady=(0, 3))
            item.pack_propagate(False)
            border = tk.Frame(item, bg="#07192b", width=3)
            border.pack(side="left", fill="y")
            button = tk.Button(
                item, text=f"   {symbol}     {title}", anchor="w",
                bg="#07192b", fg="#c7d9eb", relief="flat", bd=0,
                highlightthickness=0, activebackground="#11345a",
                activeforeground="#f3fbff", cursor="hand2",
                font=("Segoe UI", 10), padx=4,
                command=lambda ident=name: self.go(ident)
            )
            button.pack(fill="both", expand=True)
            button.bind("<Enter>", lambda e, n=name: self.hover(n, True))
            button.bind("<Leave>", lambda e, n=name: self.hover(n, False))
            self.nav_buttons[name] = (item, border, button)
        bottom = tk.Frame(self.sidebar, bg="#07192b")
        bottom.pack(side="bottom", fill="x", padx=18, pady=17)
        label(bottom, "DS TRADER  •  DESKTOP", size=8, color="#668eae",
              bold=True).pack(anchor="w")
        label(bottom, "Análise educacional · uso local",
              size=8, color="#7e97ad").pack(anchor="w", pady=(5, 0))

        self.footer = tk.Frame(root, bg=HEADER, height=43,
                               highlightthickness=1, highlightbackground=BORDER)
        self.footer.grid(row=2, column=0, sticky="ew")
        self.footer.grid_propagate(False)
        self.source = tk.StringVar(value="Fonte: dados não conectados")
        self.candles = tk.StringVar(value="Candles: aguardando")
        self.mode = tk.StringVar(value="Análise e simulação")
        self.connection = tk.StringVar(value="●  Desconectado  |  Aguardando dados")
        for variable, width in (
            (self.source, 27), (self.candles, 31), (self.mode, 29),
        ):
            box = tk.Frame(self.footer, bg=HEADER)
            box.pack(side="left", fill="y", padx=(22, 1))
            label(box, "", bg=HEADER, color="#b6d6ef", textvariable=variable,
                  size=9).pack(side="left", pady=8)
            tk.Frame(self.footer, width=1, bg="#294560").pack(
                side="left", fill="y", padx=14, pady=9)
        label(self.footer, "", bg=HEADER, color="#ff877f",
              textvariable=self.connection, size=9).pack(
                  side="right", padx=26, pady=7)

    def mount(self, notebook, frames):
        self.notebook = notebook
        self.nav_frames = frames
        notebook.bind("<<NotebookTabChanged>>", self._tab_changed, add="+")
        self.go("forex")

    def hover(self, key, entering):
        item, border, button = self.nav_buttons[key]
        if self.current == key:
            return
        button.configure(bg="#102b46" if entering else "#07192b")

    def go(self, key):
        page = self.nav_frames.get(key)
        if page is not None:
            self.notebook.select(page)
            self._activate(key)

    def _activate(self, key):
        self.current = key
        for ident, (item, border, button) in self.nav_buttons.items():
            active = ident == key
            color = "#0c3160" if active else "#07192b"
            border.configure(bg="#12a6fb" if active else "#07192b")
            button.configure(
                bg=color, fg="#80cfff" if active else "#c7d9eb",
                font=("Segoe UI", 10, "bold" if active else "normal"))
        status = {
            "overview": ("Fonte: conforme a página", "Resumo do aplicativo", "Visão geral"),
            "chart": ("Fonte: CSV / demonstração", "Histórico reproduzido", "Simulação histórica"),
            "forex": ("Fonte: Twelve Data", "Candles fechados: 1 / 5 / 15 min", "Forex por API (não IQ Option)"),
            "live": ("Fonte: captura de janela", "Pixels sem horário verificado", "Leitura visual experimental"),
            "events": ("Fonte: simulações locais", "Eventos cronológicos", "Histórico e explicações"),
            "reports": ("Fonte: relatórios locais", "Testes históricos", "Resultados simulados"),
            "config": ("Fonte: configuração local", "Regras de estratégia", "Configurações"),
            "help": ("Fonte: documentação", "Uso do aplicativo", "Ajuda"),
        }
        s, c, m = status.get(key, status["overview"])
        self.source.set(s)
        self.candles.set(c)
        self.mode.set(m)
        self.connection.set("●  Aguardando fonte verificada" if key == "forex" else
                            "●  Sem ordens reais" if key == "chart" else
                            "●  Leitura experimental" if key == "live" else
                            "●  Modo local")

    def _tab_changed(self, event=None):
        current = self.notebook.select()
        for ident, frame in self.nav_frames.items():
            if str(frame) == current:
                self._activate(ident)
                break
