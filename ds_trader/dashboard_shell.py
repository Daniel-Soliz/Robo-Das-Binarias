"""Shell compacto do DS Trader: uma barra de navegação e área central ampla.

Não contém lógica financeira nem captura dados. As páginas existentes ficam
na mesma instância de ttk.Notebook para preservar seus estados e testes.
"""
import tkinter as tk
from tkinter import ttk
from ds_trader.theme import BG, PANEL, PANEL_2, TEXT, MUTED, ACCENT

HEADER = "#111923"
BORDER = "#2b3948"
BLUE = "#243b4b"
GREEN = "#5cdbb0"
AMBER = "#e9bd78"

# Só as tarefas mais frequentes ficam sempre visíveis. As outras páginas
# permanecem montadas, com seus estados preservados, no menu Ferramentas.
NAV_ITEMS = (
    ("live", "▣", "Monitor"),
    ("radar", "◎", "Radar"),
    ("events", "◷", "Histórico"),
)
MORE_ITEMS = (
    ("overview", "Visão geral"),
    ("forex", "Forex (painel anterior)"),
    ("chart", "Simulador de CSV"),
    ("reports", "Resultados"),
    ("config", "Configurações"),
    ("help", "Ajuda"),
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
        root.geometry("1280x790")
        root.minsize(1020, 650)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # Navegação principal numa única linha. O gráfico não perde largura
        # para uma barra lateral: os três destinos frequentes estão à vista.
        self.header = tk.Frame(root, bg=HEADER, height=76,
                               highlightbackground=BORDER, highlightthickness=1)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)

        brand = tk.Frame(self.header, bg=HEADER)
        brand.pack(side="left", padx=(23, 23), pady=10)
        tk.Label(brand, text="DS", bg="#243947", fg="#b7f4fc",
                 font=("Segoe UI", 14, "bold"), padx=11, pady=8).pack(side="left", padx=(0, 12))
        brand_text = tk.Frame(brand, bg=HEADER)
        brand_text.pack(side="left")
        label(brand_text, "Trader", size=16, bold=True, bg=HEADER).pack(anchor="w")
        label(brand_text, "MONITOR INTELIGENTE", size=8,
              color="#9aaebd", bg=HEADER, bold=True).pack(anchor="w", pady=(2, 0))

        self.nav_buttons = {}
        self.nav_frames = {}
        self.current = None
        nav_bar = tk.Frame(self.header, bg="#1a2633", padx=4, pady=4)
        nav_bar.pack(side="left", padx=(3, 0))
        for name, symbol, title in NAV_ITEMS:
            item = tk.Frame(nav_bar, bg="#1a2633")
            item.pack(side="left", padx=2)
            border = tk.Frame(item, bg="#1a2633", height=2)
            button = tk.Button(
                item, text=f"{symbol}  {title}", anchor="center",
                bg="#1a2633", fg="#bccbd7", relief="flat", bd=0,
                highlightthickness=0, activebackground="#294353",
                activeforeground=TEXT, cursor="hand2",
                font=("Segoe UI", 10), padx=15, pady=8,
                command=lambda ident=name: self.go(ident),
            )
            button.pack(fill="x")
            border.pack(fill="x")
            button.bind("<Enter>", lambda e, n=name: self.hover(n, True))
            button.bind("<Leave>", lambda e, n=name: self.hover(n, False))
            self.nav_buttons[name] = (item, border, button)

        actions_menu = tk.Menu(root, tearoff=False, bg=PANEL, fg=TEXT,
                               activebackground="#304658", activeforeground="white")
        for title, command, glyph in actions:
            actions_menu.add_command(label=title, command=command)
        actions_button = tk.Menubutton(self.header, text="Arquivos  ▾",
                                       menu=actions_menu, bg=PANEL_2, fg=TEXT,
                                       activebackground="#304658", activeforeground=TEXT,
                                       relief="flat", padx=13, pady=9,
                                       font=("Segoe UI", 10), cursor="hand2")
        actions_button.pack(side="right", padx=(5, 19))
        self.more_menu = tk.Menu(root, tearoff=False, bg=PANEL, fg=TEXT,
                                 activebackground="#304658", activeforeground=TEXT)
        for key, title in MORE_ITEMS:
            self.more_menu.add_command(label=title, command=lambda page=key: self.go(page))
        more = tk.Menubutton(self.header, text="Ferramentas  ▾",
                             menu=self.more_menu, anchor="center", bg=HEADER,
                             fg="#b8c7d5", activebackground="#293c4d",
                             activeforeground=TEXT, relief="flat", bd=0,
                             padx=12, pady=9, font=("Segoe UI", 10), cursor="hand2")
        more.pack(side="right", padx=(0, 8))

        self.content = tk.Frame(root, bg=BG)
        self.content.grid(row=1, column=0, sticky="nsew")

        self.footer = tk.Frame(root, bg=HEADER, height=32,
                               highlightthickness=1, highlightbackground=BORDER)
        self.footer.grid(row=2, column=0, sticky="ew")
        self.footer.grid_propagate(False)
        self.source = tk.StringVar(value="Fonte: dados não conectados")
        self.candles = tk.StringVar(value="Candles: aguardando")
        self.mode = tk.StringVar(value="Análise e simulação")
        self.connection = tk.StringVar(value="●  Desconectado  |  Aguardando dados")
        label(self.footer, "", bg=HEADER, color="#98aab9", textvariable=self.source,
              size=9).pack(side="left", padx=20, pady=5)
        label(self.footer, "", bg=HEADER, color="#e8be83",
              textvariable=self.connection, size=9).pack(
              side="right", padx=20, pady=5)

    def mount(self, notebook, frames):
        self.notebook = notebook
        self.nav_frames = frames
        notebook.bind("<<NotebookTabChanged>>", self._tab_changed, add="+")
        self.go("radar")

    def hover(self, key, entering):
        item, border, button = self.nav_buttons[key]
        if self.current == key:
            return
        button.configure(bg="#293d4c" if entering else "#1a2633")

    def go(self, key):
        page = self.nav_frames.get(key)
        if page is not None:
            self.notebook.select(page)
            self._activate(key)

    def _activate(self, key):
        self.current = key
        for ident, (item, border, button) in self.nav_buttons.items():
            active = ident == key
            color = "#2c4554" if active else "#1a2633"
            border.configure(bg=ACCENT if active else "#1a2633")
            button.configure(
                bg=color, fg="#b1eff9" if active else "#bccbd7",
                font=("Segoe UI", 10, "bold" if active else "normal"))
        status = {
            "overview": ("Fonte: conforme a página", "Resumo do aplicativo", "Visão geral"),
            "chart": ("Fonte: CSV / demonstração", "Histórico reproduzido", "Simulação histórica"),
            "forex": ("Fonte: Twelve Data", "Candles fechados: 1 / 5 / 15 min", "Forex por API (não IQ Option)"),
            "radar": ("Fonte: Twelve Data", "Ativos favoritos por API", "Radar Forex e cripto (somente leitura)"),
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
