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

# Só as tarefas mais frequentes ficam sempre visíveis. As outras páginas
# permanecem montadas, com seus estados preservados, no menu Ferramentas.
NAV_ITEMS = (
    ("live", "▣", "Monitor"),
    ("forex", "◎", "Mercado"),
    ("chart", "⌁", "Simulador"),
)
MORE_ITEMS = (
    ("overview", "Visão geral"),
    ("events", "Histórico de sinais"),
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
        root.geometry("1320x820")
        root.minsize(1010, 665)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        # Sempre preservar ações originais de importação, demo e relatórios.
        self.header = tk.Frame(root, bg=HEADER, height=72,
                               highlightbackground=BORDER, highlightthickness=1)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)

        brand = tk.Frame(self.header, bg=HEADER)
        brand.pack(side="left", padx=(22, 12), pady=10)
        tk.Label(brand, text="◈", bg=HEADER, fg="#6a9cff",
                 font=("Segoe UI Symbol", 25, "bold")).pack(side="left", padx=(0, 9))
        label(brand, "DS Trader", size=18, bold=True, bg=HEADER).pack(side="left")
        tk.Frame(self.header, width=1, height=33, bg="#35516a").pack(side="left")
        label(self.header, "MONITORAMENTO   •   SEM ORDENS REAIS",
              size=9, color="#6fa5df", bg=HEADER, bold=True).pack(
                  side="left", padx=(20, 10))

        actions_menu = tk.Menu(root, tearoff=False, bg=PANEL, fg=TEXT,
                               activebackground="#244360", activeforeground="white")
        for title, command, glyph in actions:
            actions_menu.add_command(label=title, command=command)
        actions_button = tk.Menubutton(self.header, text="Arquivos  ▾",
                                       menu=actions_menu, bg="#172c44", fg=TEXT,
                                       activebackground="#244360", activeforeground=TEXT,
                                       relief="flat", padx=17, pady=8,
                                       font=("Segoe UI", 10), cursor="hand2")
        actions_button.pack(side="right", padx=20)

        stage = tk.Frame(root, bg=BG)
        stage.grid(row=1, column=0, sticky="nsew")
        stage.grid_rowconfigure(0, weight=1)
        stage.grid_columnconfigure(1, weight=1)
        self.sidebar = tk.Frame(stage, bg="#07192b", width=190)
        self.sidebar.grid(row=0, column=0, sticky="ns")
        self.sidebar.grid_propagate(False)
        tk.Frame(stage, width=1, bg=BORDER).grid(row=0, column=0, sticky="nse")
        self.content = tk.Frame(stage, bg=BG)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.nav_buttons = {}
        self.nav_frames = {}
        self.current = None

        space = tk.Frame(self.sidebar, bg="#07192b", height=22)
        space.pack(fill="x")
        for name, symbol, title in NAV_ITEMS:
            item = tk.Frame(self.sidebar, bg="#07192b", height=49)
            item.pack(fill="x", padx=(12, 8), pady=(0, 3))
            item.pack_propagate(False)
            border = tk.Frame(item, bg="#07192b", width=3)
            border.pack(side="left", fill="y")
            button = tk.Button(
                item, text=f"  {symbol}   {title}", anchor="w",
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
        self.more_menu = tk.Menu(root, tearoff=False, bg=PANEL, fg=TEXT,
                                 activebackground="#244360", activeforeground=TEXT)
        for key, title in MORE_ITEMS:
            self.more_menu.add_command(label=title, command=lambda page=key: self.go(page))
        more = tk.Menubutton(self.sidebar, text="  ⚙   Ferramentas  ▾",
                             menu=self.more_menu, anchor="w", bg="#07192b",
                             fg="#c7d9eb", activebackground="#11345a",
                             activeforeground=TEXT, relief="flat", bd=0,
                             padx=10, pady=13, font=("Segoe UI", 10), cursor="hand2")
        more.pack(fill="x", padx=(12, 8), pady=(12, 0))
        bottom = tk.Frame(self.sidebar, bg="#07192b")
        bottom.pack(side="bottom", fill="x", padx=18, pady=17)
        label(bottom, "DS TRADER  •  DESKTOP", size=8, color="#668eae",
              bold=True).pack(anchor="w")
        label(bottom, "Análise educacional · uso local",
              size=8, color="#7e97ad").pack(anchor="w", pady=(5, 0))

        self.footer = tk.Frame(root, bg=HEADER, height=36,
                               highlightthickness=1, highlightbackground=BORDER)
        self.footer.grid(row=2, column=0, sticky="ew")
        self.footer.grid_propagate(False)
        self.source = tk.StringVar(value="Fonte: dados não conectados")
        self.candles = tk.StringVar(value="Candles: aguardando")
        self.mode = tk.StringVar(value="Análise e simulação")
        self.connection = tk.StringVar(value="●  Desconectado  |  Aguardando dados")
        label(self.footer, "", bg=HEADER, color="#a8bdd1", textvariable=self.source,
              size=9).pack(side="left", padx=20, pady=6)
        label(self.footer, "", bg=HEADER, color="#ff877f",
              textvariable=self.connection, size=9).pack(
              side="right", padx=20, pady=6)

    def mount(self, notebook, frames):
        self.notebook = notebook
        self.nav_frames = frames
        notebook.bind("<<NotebookTabChanged>>", self._tab_changed, add="+")
        self.go("live")

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
