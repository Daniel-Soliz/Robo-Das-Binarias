"""Tela de configuracoes DS Trader AI: controles reais e parametros preservados."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from ds_trader.theme import BG, PANEL, PANEL_2, TEXT, MUTED, ACCENT

EDGE = "#23475d"
AMBER = "#ffbd64"


def text(parent, value, size=10, color=TEXT, bold=False, **kw):
    return tk.Label(parent, text=value, bg=parent.cget("bg"), fg=color,
                    anchor="w", justify="left", font=("Segoe UI", size,
                    "bold" if bold else "normal"), **kw)


def panel(parent, title, subtitle):
    wrapper = tk.Frame(parent, bg=PANEL, highlightbackground=EDGE,
                       highlightthickness=1, padx=16, pady=12)
    text(wrapper, title, size=11, color=ACCENT, bold=True).pack(anchor="w")
    text(wrapper, subtitle, color=MUTED, size=9).pack(anchor="w", pady=(3, 12))
    return wrapper


def render_settings(parent, root, variables, stored, defaults, labels,
                    on_save, monitor, radar):
    """Os campos do replay continuam ligados às variáveis originais.

    Nenhum botão 'Conectado' falso: fonte é exibida segundo a configuração.
    """
    canvas = tk.Canvas(parent, bg=BG, highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(fill="both", expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)
    body = tk.Frame(canvas, bg=BG, padx=15, pady=12)
    window = canvas.create_window((0, 0), window=body, anchor="nw")
    body.bind("<Configure>", lambda _evt: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window, width=event.width))
    text(body, "CONFIGURAÇÕES DO SISTEMA", size=21, bold=True).pack(anchor="w")
    text(body, "Capture a IQ Option e configure somente as fontes disponíveis. "
         "Os parâmetros históricos são salvos em armazenamento local.",
         color=MUTED, size=10, wraplength=1000).pack(anchor="w", pady=(6, 15))
    sections = tk.Frame(body, bg=BG)
    sections.pack(fill="x")
    sections.grid_columnconfigure(0, weight=1)
    sections.grid_columnconfigure(1, weight=1)
    capture = panel(sections, "CAPTURA E RECONHECIMENTO",
                    "Par e OTC exigem confirmação visual; não alteramos a corretora.")
    capture.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    check = tk.Checkbutton(capture, text="Detectar janela da IQ Option automaticamente",
                           variable=monitor._auto_enabled, command=monitor._auto_toggled,
                           bg=PANEL, fg=TEXT, selectcolor=PANEL_2,
                           activebackground=PANEL, activeforeground=TEXT)
    check.pack(anchor="w", pady=(0, 12))
    selector = tk.Frame(capture, bg=PANEL)
    selector.pack(fill="x")
    text(selector, "PERÍODO INFORMADO NO MONITOR", 9, MUTED).pack(side="left")
    ttk.Combobox(selector, state="readonly", textvariable=monitor.timeframe,
                 values=("M1", "M5", "M15"), width=7).pack(side="left", padx=14)
    text(capture, "OCR local incluso no instalador. Em OTC não é possível cruzar "
         "preços com fontes públicas como se fossem da IQ Option.",
         color=AMBER, size=9, wraplength=440).pack(anchor="w", pady=(14, 0))
    source = panel(sections, "FONTES DE MERCADO",
                   "Criptomoedas públicas; Forex requer fornecedor habilitado.")
    source.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    text(source, "● Binance /USDT — WebSocket público", color=ACCENT, size=9).pack(anchor="w")
    text(source, "● Kraken /USD — dados públicos", color=ACCENT, size=9).pack(anchor="w", pady=(5, 9))
    text(source, "TWELVE DATA · CHAVE OPCIONAL PARA FOREX",
         color=MUTED, size=9).pack(anchor="w", pady=(4, 3))
    ttk.Entry(source, textvariable=radar.key, show="●").pack(fill="x")
    text(source, "Configurar a chave não confirma correspondência com a IQ Option.",
         color=AMBER, size=9, wraplength=420).pack(anchor="w", pady=(10, 0))
    settings = panel(body, "PARÂMETROS DE REPRODUÇÃO HISTÓRICA",
                     "Mantidos do aplicativo anterior. Não mudam automaticamente a análise visual.")
    settings.pack(fill="x", pady=(12, 0))
    grid = tk.Frame(settings, bg=PANEL)
    grid.pack(fill="x")
    for col in range(2):
        grid.grid_columnconfigure(col, weight=1)
    for index, (name, default) in enumerate(defaults.items()):
        field = tk.Frame(grid, bg=PANEL, padx=5, pady=6)
        field.grid(row=index // 2, column=index % 2, sticky="ew")
        text(field, labels[name], size=9, color=MUTED, wraplength=360).pack(anchor="w")
        variable = tk.StringVar(value=str(stored.get(name, default)))
        variables[name] = variable
        if name == "tie":
            widget = ttk.Combobox(field, textvariable=variable,
                                   values=("refund", "loss"), state="readonly")
        else:
            widget = ttk.Entry(field, textvariable=variable)
        widget.pack(fill="x", pady=(4, 0))
    tk.Button(settings, text="Salvar parâmetros históricos", command=on_save,
              bg="#137e97", fg="#ffffff", relief="flat", bd=0,
              font=("Segoe UI", 10, "bold"), padx=18, pady=10).pack(anchor="e", pady=(16, 0))
    text(body, "O DS Trader AI não envia ordens e não mede taxa de acerto com pixels.",
         color=MUTED, size=9).pack(anchor="w", pady=15)
    return canvas
