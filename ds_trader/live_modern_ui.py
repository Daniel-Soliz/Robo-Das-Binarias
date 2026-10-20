"""Painel moderno de monitoramento local: gráfico à esquerda e leitura à direita.

A interface não cria ordens; somente apresenta análises recebidas da thread.
A região da corretora precisa permanecer visível, sem cobertura desta janela.
"""
from __future__ import annotations

from datetime import datetime
from queue import Empty
import tkinter as tk
from tkinter import ttk, messagebox

from ds_trader.live_ui import RegionPicker
from ds_trader.live_screen import ScreenMonitor
from ds_trader.live_presentation import presentation_for


BG = "#08111f"
PANEL = "#101c2d"
PANEL_2 = "#15243a"
EDGE = "#263b53"
TEXT = "#e9f3ff"
MUTED = "#91a5bb"
CYAN = "#46c9ef"
GREEN = "#41d8a4"
RED = "#ff7584"
AMBER = "#ffc56b"

SIDE_COLORS = {"CALL": GREEN, "PUT": RED, "AGUARDAR": AMBER}


def _label(parent, text="", *, size=10, weight="normal", color=TEXT,
           bg=None, **kwargs):
    return tk.Label(
        parent, text=text, bg=bg or parent.cget("bg"), fg=color,
        font=("Segoe UI", size, weight), anchor="w",
        justify="left", **kwargs,
    )


def _button(parent, text, command, *, primary=False, stop=False):
    bg = "#0875a6" if primary else "#57313d" if stop else PANEL_2
    hover = "#1593c3" if primary else "#70414d" if stop else "#243d59"
    widget = tk.Button(
        parent, text=text, command=command, bg=bg, fg=TEXT,
        activebackground=hover, activeforeground="#ffffff",
        font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0,
        padx=18, pady=10, cursor="hand2", disabledforeground="#788b9f",
    )
    return widget


class LiveScreenTab:
    """Interface com preview responsivo e painel lateral persistente.

    Preserva a API utilizada por App e pelos smoke tests: start, stop,
    selected, active, screen_view e shutdown.
    """

    def __init__(self, parent, root):
        self.root = root
        self.region = None
        self.monitor = None
        self.active = False
        self.after_id = None
        self.preview_image = None
        self.last_frame = None
        self.timeframe = tk.StringVar(value="M1")
        self.status = tk.StringVar(value="DESLIGADO · Selecione a área do gráfico")
        self.next_opinion = tk.StringVar(value="AGUARDAR")
        self.structures = tk.StringVar(value="Aguardando análise")
        self.observation = tk.StringVar(value="Selecione uma região para iniciar.")
        self.meta_text = tk.StringVar(value="Sem região configurada")
        self.last_update = tk.StringVar(value="Última leitura —")
        self.pattern_text = tk.StringVar(value="Aguardando reconhecimento")
        self.structure_text = tk.StringVar(value="Aguardando reconhecimento")
        self.summary_text = tk.StringVar(value="Nenhum dado recebido")
        self.evidence_text = tk.StringVar(value="—")
        self.signal_subtitle = tk.StringVar(value="CAPTURA NÃO INICIADA")
        self.quality_status = tk.StringVar(value="Sem dados")
        self._picker = None

        container = tk.Frame(parent, bg=BG, padx=17, pady=15)
        container.pack(fill="both", expand=True)
        self.container = container

        # Cabeçalho editorial com hierarquia visual de produto, não formulário.
        header = tk.Frame(container, bg=BG)
        header.pack(fill="x", pady=(0, 12))
        heading = tk.Frame(header, bg=BG)
        heading.pack(side="left", fill="x", expand=True)
        _label(heading, "MONITOR DE GRÁFICOS", size=20, weight="bold").pack(anchor="w")
        _label(
            heading, "Veja seu gráfico à esquerda e a análise técnica ao lado · somente leitura",
            size=10, color=MUTED,
        ).pack(anchor="w", pady=(3, 0))
        self.online_badge = _label(
            header, "●  MONITORAMENTO DESLIGADO", color=AMBER,
            size=9, weight="bold", bg=PANEL_2, padx=12, pady=9,
        )
        self.online_badge.pack(side="right")

        toolbar = tk.Frame(container, bg=PANEL, highlightbackground=EDGE,
                           highlightthickness=1, padx=12, pady=10)
        toolbar.pack(fill="x", pady=(0, 13))
        self.pick_btn = _button(toolbar, "⌖  Selecionar gráfico", self.select)
        self.pick_btn.pack(side="left", padx=(0, 9))
        self.start_btn = _button(toolbar, "▶  Iniciar análise", self.start, primary=True)
        self.start_btn.configure(state="disabled")
        self.start_btn.pack(side="left", padx=(0, 9))
        self.stop_btn = _button(toolbar, "■  Parar", self.stop, stop=True)
        self.stop_btn.configure(state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 15))
        _label(toolbar, "Período informado:", size=9, color=MUTED).pack(side="left", padx=(4, 7))
        self.period_select = ttk.Combobox(
            toolbar, values=("M1", "M5", "M15"), textvariable=self.timeframe,
            state="readonly", width=5, font=("Segoe UI", 10),
        )
        self.period_select.pack(side="left")
        self.meta_label = _label(toolbar, "", color=MUTED, size=9, textvariable=self.meta_text)
        self.meta_label.pack(side="right")

        # A área principal escala horizontalmente: o gráfico recebe o espaço livre.
        workspace = tk.Frame(container, bg=BG)
        workspace.pack(fill="both", expand=True)
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, minsize=342)

        left = tk.Frame(workspace, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 13))
        left_head = tk.Frame(left, bg=PANEL, padx=13, pady=11)
        left_head.pack(fill="x")
        _label(left_head, "PRÉVIA DA TELA", weight="bold", size=10).pack(side="left")
        self.preview_marker = _label(left_head, "●  SEM CAPTURA", size=9, color=MUTED)
        self.preview_marker.pack(side="right")

        preview_area = tk.Frame(left, bg="#070f1c")
        preview_area.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        self.image_label = tk.Label(
            preview_area, bg="#070f1c", fg=MUTED, font=("Segoe UI", 11),
            text="Sua tela aparecerá aqui.\n\nSelecione somente a área dos candles\n"
                 "e mantenha a plataforma visível ao lado.",
            justify="center", anchor="center",
        )
        self.image_label.pack(fill="both", expand=True)
        self.image_label.bind("<Configure>", self._resize_preview)

        left_bottom = tk.Frame(left, bg=PANEL, padx=13, pady=4)
        left_bottom.pack(fill="x")
        _label(left_bottom, "", size=9, color=MUTED,
               textvariable=self.last_update).pack(anchor="w", pady=(0, 5))
        _label(
            left_bottom,
            "Dica: deixe o gráfico e o DS Trader lado a lado, sem sobreposição.",
            size=9, color=CYAN,
        ).pack(anchor="w", pady=(0, 7))

        right = tk.Frame(workspace, bg=BG, width=342)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_propagate(False)
        right.grid_columnconfigure(0, weight=1)

        signal_card = tk.Frame(right, bg=PANEL, highlightbackground=EDGE,
                               highlightthickness=1, padx=18, pady=14)
        signal_card.pack(fill="x", pady=(0, 10))
        _label(signal_card, "HIPÓTESE · PRÓXIMA VELA", color=MUTED,
               size=9, weight="bold").pack(anchor="w")
        self.signal_label = _label(signal_card, "", textvariable=self.next_opinion,
                                   size=32, color=AMBER, weight="bold")
        self.signal_label.pack(anchor="w", pady=(5, 2))
        self.signal_context = _label(
            signal_card, "", textvariable=self.signal_subtitle,
            color=AMBER, size=9, weight="bold", wraplength=298,
        )
        self.signal_context.pack(anchor="w")
        _label(
            signal_card,
            "CALL = alta  ·  PUT = baixa  ·  AGUARDAR = sem hipótese",
            size=8, color=MUTED, wraplength=300,
        ).pack(anchor="w", pady=(10, 0))

        analysis_card = tk.Frame(right, bg=PANEL, highlightbackground=EDGE,
                                 highlightthickness=1, padx=16, pady=13)
        analysis_card.pack(fill="x", pady=(0, 10))
        _label(analysis_card, "LEITURA TÉCNICA", size=10, weight="bold").pack(anchor="w", pady=(0, 9))
        for title, var in (
            ("ESTADO DA CAPTURA", self.quality_status),
            ("PADRÕES DE CANDLE", self.pattern_text),
            ("ESTRUTURAS · LTA/LTB", self.structure_text),
        ):
            _label(analysis_card, title, size=8, color=MUTED, weight="bold").pack(anchor="w", pady=(4, 2))
            _label(analysis_card, "", textvariable=var,
                   wraplength=300, size=9).pack(anchor="w", pady=(0, 4))

        detail_card = tk.Frame(right, bg=PANEL, highlightbackground=EDGE,
                               highlightthickness=1, padx=16, pady=12)
        detail_card.pack(fill="both", expand=True)
        _label(detail_card, "POR QUE ESTA LEITURA?", size=10, weight="bold").pack(anchor="w", pady=(0, 7))
        self.detail_text = tk.Text(
            detail_card, height=5, wrap="word", bg=PANEL, fg="#c0d3e6",
            selectbackground="#234d71", insertbackground=TEXT,
            relief="flat", bd=0, highlightthickness=0, padx=0, pady=0,
            font=("Segoe UI", 9),
        )
        self.detail_text.pack(fill="both", expand=True)
        self._set_detail("Aguardando captura. O app não envia ordens e não "
                         "confirma o fechamento da vela pela imagem.")

        notice = tk.Frame(container, bg="#142436", highlightbackground=EDGE,
                          highlightthickness=1, padx=12, pady=8)
        notice.pack(fill="x", pady=(12, 0))
        _label(
            notice,
            "LEITURA EXPERIMENTAL  ·  CALL/PUT não é sinal validado, "
            "não fornece horário de entrada, vencimento nem probabilidade de acerto.",
            size=9, color="#aac0d5", bg="#142436", wraplength=1050,
        ).pack(anchor="w")

    def _set_detail(self, text):
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def _resize_preview(self, _event=None):
        if self.last_frame is None:
            return
        from PIL import Image, ImageTk
        available_w = self.image_label.winfo_width()
        available_h = self.image_label.winfo_height()
        if available_w < 80 or available_h < 80:
            return
        frame = self.last_frame.copy()
        frame.thumbnail((available_w - 12, available_h - 12), Image.Resampling.LANCZOS)
        self.preview_image = ImageTk.PhotoImage(frame)
        self.image_label.configure(image=self.preview_image, text="")

    def _overlaps_selected_region(self):
        """Impede capturar o próprio DS Trader em vez da plataforma."""
        if self.region is None or not self.root.winfo_viewable():
            return False
        ax, ay = self.region.left, self.region.top
        aw, ah = self.region.width, self.region.height
        bx, by = self.root.winfo_rootx(), self.root.winfo_rooty()
        bw, bh = self.root.winfo_width(), self.root.winfo_height()
        width = max(0, min(ax + aw, bx + bw) - max(ax, bx))
        height = max(0, min(ay + ah, by + bh) - max(ay, by))
        return width * height > aw * ah * .08

    def select(self):
        if self.active:
            self.stop()
        try:
            # O seletor existente trabalha em coordenadas globais do desktop.
            self._picker = RegionPicker(self.root, self.selected)
            self.status.set("Arraste somente sobre os candles. Esc cancela.")
        except Exception as exc:
            messagebox.showerror("Selecionar gráfico", str(exc), parent=self.root)

    def selected(self, region):
        self.region = region
        self.meta_text.set(f"{region.width} × {region.height} px")
        self.status.set("Área escolhida · Clique em Iniciar análise")
        self.start_btn.configure(state="normal")
        self.last_frame = None
        self.preview_image = None
        self.image_label.configure(
            image="", text="Área selecionada.\n\nClique em Iniciar análise para acompanhar.")
        self.next_opinion.set("AGUARDAR")
        self.signal_subtitle.set("AGUARDANDO PRIMEIRA LEITURA")
        self._set_detail("Nenhuma imagem foi capturada ainda. "
                         "Mantenha a IQ Option visível ao lado do DS Trader.")

    def start(self):
        if self.active:
            return
        if self.region is None:
            messagebox.showinfo("DS Trader", "Selecione primeiro a região do gráfico.",
                                parent=self.root)
            return
        self.monitor = ScreenMonitor(self.region, interval_seconds=1.2)
        self.active = True
        self.pick_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.online_badge.configure(text="●  MONITORAMENTO ATIVO", fg=GREEN)
        self.preview_marker.configure(text="●  RECEBENDO IMAGENS", fg=CYAN)
        self.status.set("Captura local iniciada")
        self.poll()

    def _present(self, result):
        obscured = self._overlaps_selected_region()
        state = presentation_for(result, obscured=obscured)
        self.next_opinion.set(state.side)
        self.signal_label.configure(fg=SIDE_COLORS[state.side])
        self.signal_context.configure(fg=SIDE_COLORS[state.side])
        self.signal_subtitle.set(state.subtitle)
        self.status.set(state.status)
        self.quality_status.set("Gráfico encoberto" if obscured else
                                "Recorte legível" if result.valid_roi else "Leitura insuficiente")
        self.pattern_text.set(state.pattern)
        self.structure_text.set(state.structure)
        self._set_detail(state.detail)
        self.observation.set(state.detail)
        self.structures.set(state.structure)
        try:
            ts = datetime.fromisoformat(result.captured_at).astimezone()
            local_time = ts.strftime("%H:%M:%S")
        except (TypeError, ValueError):
            local_time = "—"
        self.last_update.set(
            f"Última captura: {local_time} (horário do PC)  ·  "
            f"{state.detected_label}  ·  {self.timeframe.get()} informado"
        )

    def poll(self):
        self.after_id = None
        if not self.active:
            return
        try:
            while True:
                item = self.monitor.results.get_nowait()
                if item[0] == "error":
                    self.stop()
                    self.quality_status.set("Erro de captura")
                    self.status.set(item[1])
                    self._set_detail(item[1])
                    return
                result, frame = item
                self.last_frame = frame
                self._resize_preview()
                self._present(result)
        except Empty:
            pass
        self.after_id = self.root.after(170, self.poll)

    def stop(self):
        self.active = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.monitor is not None:
            self.monitor.stop()
            self.monitor = None
        self.pick_btn.configure(state="normal")
        self.start_btn.configure(state="normal" if self.region is not None else "disabled")
        self.stop_btn.configure(state="disabled")
        self.online_badge.configure(text="●  MONITORAMENTO DESLIGADO", fg=AMBER)
        self.preview_marker.configure(text="●  PAUSADO", fg=MUTED)
        self.next_opinion.set("AGUARDAR")
        self.signal_label.configure(fg=AMBER)
        self.signal_context.configure(fg=AMBER)
        self.signal_subtitle.set("CAPTURA INTERROMPIDA")
        self.status.set("Monitoramento parado")
        self.quality_status.set("Desconectado")
        self._set_detail("A captura foi interrompida. A última imagem pode "
                         "continuar na prévia, mas não há análise em andamento.")

    def shutdown(self):
        self.stop()
