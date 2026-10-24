"""Painel moderno de monitoramento local: gráfico à esquerda e leitura à direita.

A interface não cria ordens; somente apresenta análises recebidas da thread.
A região da corretora precisa permanecer visível, sem cobertura desta janela.
"""
from __future__ import annotations

from datetime import datetime
from queue import Empty
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox

from ds_trader.live_ui import RegionPicker
from ds_trader.live_screen import ScreenMonitor
from ds_trader.m1_cycle import M1Cycle
from ds_trader.active_tracking import (ActiveAssetTracking, focus_identity,
                                       format_active_focus)
from ds_trader.live_presentation import presentation_for, screen_region_is_obscured
from ds_trader.technical_score import score_visual
from ds_trader.theme import BG, PANEL, PANEL_2, TEXT, MUTED, ACCENT
from ds_trader.window_capture import (WindowCaptureError, select_window_for_region,
                                      enumerate_windows, IqOptionDiscovery, WindowTarget)


EDGE = "#2b3948"
CYAN = ACCENT
GREEN = "#5cdbb0"
RED = "#fd8991"
AMBER = "#e9bd78"

SIDE_COLORS = {"CALL": GREEN, "PUT": RED, "AGUARDAR": AMBER}


def _label(parent, text="", *, size=10, weight="normal", color=TEXT,
           bg=None, **kwargs):
    return tk.Label(
        parent, text=text, bg=bg or parent.cget("bg"), fg=color,
        font=("Segoe UI", size, weight), anchor="w",
        justify="left", **kwargs,
    )


def _button(parent, text, command, *, primary=False, stop=False):
    bg = "#187d91" if primary else "#393037" if stop else PANEL_2
    hover = "#2395a9" if primary else "#5a3c47" if stop else "#304456"
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
        self.window_target: WindowTarget | None = None
        self.monitor = None
        self.active = False
        self.after_id = None
        self.preview_image = None
        self.last_frame = None
        self._last_preview_at = None
        self._last_preview_size = None
        self._detail_cache = None
        self._stale_notified = False
        self._last_rendered_at = 0.0
        self._details_open = False
        self._radar_rows = ()
        self.timeframe = tk.StringVar(value="M5")
        self.m1_cycle = M1Cycle()
        self.cycle_message = tk.StringVar(
            value=self.m1_cycle.block_visual("M5").reason
        )
        self.active_tracking = ActiveAssetTracking()
        self._market_key_supplier = lambda: ""
        self.active_context = tk.StringVar(
            value="M5 · AGUARDAR identificação do par na IQ Option. "
                  "Não há entrada operacional validada."
        )
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
        self.visual_bias = tk.StringVar(value="SEM VANTAGEM CLARA")
        self.visual_reason = tk.StringVar(value="Aguardando gráfico.")
        self.quality_status = tk.StringVar(value="Sem dados")
        self.confluence = tk.StringVar(value="AGUARDAR · pontuação não calculada")
        self.speed_status = tk.StringVar(value="MOTOR PRONTO  ·  SEM CAPTURA")
        self._picker = None
        self._auto_enabled = tk.BooleanVar(value=sys.platform == "win32")
        self._auto_paused = False
        self._auto_region = False
        self._auto_guard = IqOptionDiscovery()
        self._auto_id = None

        self.latest_assessment = None
        container = tk.Frame(parent, bg=BG, padx=11, pady=9)
        container.pack(fill="both", expand=True)
        self.container = container

        # Fluxo principal: selecionar o gráfico, iniciar, acompanhar o estado.
        header = tk.Frame(container, bg=BG)
        header.pack(fill="x", pady=(0, 7))
        heading = tk.Frame(header, bg=BG)
        heading.pack(side="left", fill="x", expand=True)
        _label(heading, "GRÁFICO AO VIVO", size=17, weight="bold").pack(anchor="w")
        _label(
            heading, "Gráfico, estruturas e cenário da próxima vela — tudo em um lugar.",
            size=10, color=MUTED,
        ).pack(anchor="w", pady=(3, 0))
        self.online_badge = _label(
            header, "●  MONITORAMENTO DESLIGADO", color=AMBER,
            size=9, weight="bold", bg=PANEL_2, padx=10, pady=7,
        )
        self.online_badge.pack(side="right")

        toolbar = tk.Frame(container, bg=PANEL, highlightbackground=EDGE,
                           highlightthickness=1, padx=13, pady=10)
        toolbar.pack(fill="x", pady=(0, 8))
        self.pick_btn = _button(toolbar, "1  Selecionar janela", self.select)
        self.pick_btn.pack(side="left", padx=(0, 8))
        self.start_btn = _button(toolbar, "2  Iniciar monitor", self.start, primary=True)
        self.start_btn.configure(state="disabled")
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn = _button(toolbar, "Parar", self.stop, stop=True)
        self.stop_btn.configure(state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 18))
        self.auto_check = tk.Checkbutton(
            toolbar, text="Detectar IQ Option", variable=self._auto_enabled,
            command=self._auto_toggled, bg=PANEL, fg=TEXT,
            selectcolor=PANEL_2, activebackground=PANEL,
            activeforeground=TEXT, font=("Segoe UI", 9),
        )
        self.auto_check.pack(side="left", padx=(0, 10))
        _label(toolbar, "GRÁFICO", size=8, weight="bold", color=MUTED).pack(side="left", padx=(2, 7))
        self.period_select = ttk.Combobox(
            toolbar, values=("M1", "M5", "M15"), textvariable=self.timeframe,
            state="readonly", width=5, font=("Segoe UI", 10),
        )
        self.period_select.pack(side="left")
        self.timeframe.trace_add("write", lambda *_: self._refresh_cycle_guard())
        self.meta_label = _label(toolbar, "", color=MUTED, size=9, textvariable=self.meta_text)
        self.meta_label.pack(side="right")

        # A área principal escala horizontalmente: o gráfico recebe o espaço livre.
        workspace = tk.Frame(container, bg=BG)
        workspace.pack(fill="both", expand=True)
        workspace.grid_rowconfigure(0, weight=1)
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_columnconfigure(1, minsize=365)

        left = tk.Frame(workspace, bg=PANEL, highlightbackground=EDGE, highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        left_head = tk.Frame(left, bg=PANEL, padx=16, pady=12)
        left_head.pack(fill="x")
        _label(left_head, "GRÁFICO AO VIVO · Captura IQ Option", weight="bold", size=10).pack(side="left")
        self.preview_marker = _label(left_head, "●  SEM CAPTURA", size=9, color=MUTED)
        self.preview_marker.pack(side="right")

        preview_area = tk.Frame(left, bg="#0b141e")
        preview_area.pack(fill="both", expand=True, padx=11, pady=(0, 9))
        self.image_label = tk.Label(
            preview_area, bg="#0b141e", fg=MUTED, font=("Segoe UI", 12),
            text="Seu gráfico aparecerá aqui\n\nSelecione a janela da IQ Option\ne marque somente a região das velas.",
            justify="center", anchor="center",
        )
        self.image_label.pack(fill="both", expand=True)
        self.image_label.bind("<Configure>", self._resize_preview)

        left_bottom = tk.Frame(left, bg=PANEL, padx=16, pady=5)
        left_bottom.pack(fill="x")
        _label(left_bottom, "", size=9, color=MUTED,
               textvariable=self.last_update).pack(anchor="w", pady=(0, 5))
        _label(left_bottom, "", textvariable=self.speed_status,
               size=9, color=CYAN).pack(anchor="w", pady=(0, 3))

        right_holder = tk.Frame(workspace, bg=BG, width=365)
        right_holder.grid(row=0, column=1, sticky="nsew")
        right_holder.grid_propagate(False)
        right_canvas = tk.Canvas(right_holder, bg=BG, highlightthickness=0, bd=0)
        right_scroll = ttk.Scrollbar(right_holder, orient="vertical",
                                     command=right_canvas.yview)
        right_scroll.pack(side="right", fill="y")
        right_canvas.pack(side="left", fill="both", expand=True)
        right_canvas.configure(yscrollcommand=right_scroll.set)
        right = tk.Frame(right_canvas, bg=BG)
        window = right_canvas.create_window((0, 0), window=right, anchor="nw")
        right.bind("<Configure>", lambda _e: right_canvas.configure(
            scrollregion=right_canvas.bbox("all")))
        right_canvas.bind("<Configure>", lambda e: right_canvas.itemconfigure(
            window, width=e.width))
        self.right_canvas = right_canvas

        signal_card = tk.Frame(right, bg=PANEL, highlightbackground=EDGE,
                               highlightthickness=1, padx=18, pady=16)
        signal_card.pack(fill="x", pady=(0, 12))
        _label(signal_card, "ANÁLISE DE CANDLES · PRÓXIMA VELA", color=CYAN,
               size=9, weight="bold").pack(anchor="w", pady=(0, 4))
        self.visual_bias_label = _label(
            signal_card, "", textvariable=self.visual_bias, size=20,
            color=CYAN, weight="bold", wraplength=310,
        )
        self.visual_bias_label.pack(anchor="w", pady=(4, 5))
        _label(signal_card, "", textvariable=self.visual_reason,
               size=10, color=MUTED, wraplength=310).pack(anchor="w", pady=(1, 12))
        tk.Frame(signal_card, height=1, bg=EDGE).pack(fill="x", pady=(0, 10))
        validation = tk.Frame(signal_card, bg=PANEL)
        validation.pack(fill="x")
        _label(validation, "VALIDAÇÃO", color=MUTED, size=8,
               weight="bold").pack(side="left", padx=(0, 14))
        self.signal_label = _label(validation, "", textvariable=self.next_opinion,
                                   size=13, color=AMBER, weight="bold")
        self.signal_label.pack(side="left")
        self.signal_context = _label(
            signal_card, "", textvariable=self.signal_subtitle,
            color=AMBER, size=9, weight="bold", wraplength=310,
        )
        self.signal_context.pack(anchor="w", pady=(4, 0))
        _label(
            signal_card,
            "Leitura educacional · nenhuma ordem é enviada",
            size=8, color=MUTED, wraplength=310,
        ).pack(anchor="w", pady=(8, 0))

        score_card = tk.Frame(right, bg=PANEL, highlightbackground=EDGE,
                              highlightthickness=1, padx=16, pady=12)
        score_card.pack(fill="x", pady=(0, 9))
        _label(score_card, "ALINHAMENTO TÉCNICO · NÃO É CHANCE DE ACERTO",
               color=CYAN, size=9, weight="bold").pack(anchor="w")
        _label(score_card, "", textvariable=self.confluence,
               color=TEXT, size=12, weight="bold",
               wraplength=310).pack(anchor="w", pady=(8, 2))

        analysis_card = tk.Frame(right, bg=PANEL, highlightbackground=EDGE,
                                 highlightthickness=1, padx=16, pady=13)
        analysis_card.pack(fill="x", pady=(0, 12))
        _label(analysis_card, "PADRÕES E CONFLUÊNCIAS", size=10, weight="bold").pack(anchor="w", pady=(0, 7))
        for title, var in (
            ("LEITURA", self.quality_status),
            ("PADRÕES", self.pattern_text),
            ("TENDÊNCIA / NÍVEIS", self.structure_text),
        ):
            _label(analysis_card, title, size=8, color=MUTED, weight="bold").pack(anchor="w", pady=(3, 1))
            _label(analysis_card, "", textvariable=var,
                   wraplength=310, size=9).pack(anchor="w", pady=(0, 4))

        self.details_toggle = _button(right, "Raciocínio da análise  ▾", self.toggle_details)
        self.details_toggle.pack(fill="x", pady=(0, 8))
        self.advanced_content = tk.Frame(right, bg=BG)
        m1_card = tk.Frame(self.advanced_content, bg="#202333", highlightbackground=EDGE,
                           highlightthickness=1, padx=11, pady=8)
        m1_card.pack(fill="x", pady=(0, 8))
        _label(m1_card, "VALIDAÇÃO M1", size=9, weight="bold",
               color=AMBER, bg="#202333").pack(anchor="w")
        _label(m1_card, "", textvariable=self.cycle_message,
               size=9, color="#f1d5ad", bg="#202333",
               wraplength=275).pack(anchor="w", pady=(4, 0))

        detail_card = tk.Frame(self.advanced_content, bg=PANEL, highlightbackground=EDGE,
                               highlightthickness=1, padx=12, pady=10)
        detail_card.pack(fill="both", expand=True)
        _label(detail_card, "EXPLICAÇÃO COMPLETA", size=9, weight="bold").pack(anchor="w", pady=(0, 5))
        self.detail_text = tk.Text(
            detail_card, height=6, wrap="word", bg=PANEL, fg="#c0d3e6",
            selectbackground="#234d71", insertbackground=TEXT,
            relief="flat", bd=0, highlightthickness=0, padx=0, pady=0,
            font=("Segoe UI", 9),
        )
        self.detail_text.pack(fill="both", expand=True)
        self._set_detail("Aguardando captura. O app não envia ordens e não "
                         "confirma o fechamento da vela pela imagem.")

        focus = tk.Frame(container, bg=PANEL, padx=12, pady=10,
                         highlightbackground=EDGE, highlightthickness=1)
        focus.pack(fill="x", pady=(10, 0))
        _label(focus, "ATIVO DETECTADO · HISTÓRICO M5 ATÉ 24 HORAS",
               size=9, weight="bold", color=ACCENT).pack(anchor="w", pady=(0, 5))
        _label(focus, "", textvariable=self.active_context, size=9,
               color=TEXT, wraplength=1040).pack(fill="x")

        # Preserve the old Radar callback and Treeview contract without
        # wasting vertical space on a duplicated table. Radar has its own tab.
        self.radar_preview = ttk.Treeview(container,
            columns=("market", "status", "trend", "closed"), show="tree headings")
        self.radar_preview.heading("#0", text="ATIVO")
        for column in ("market", "status", "trend", "closed"):
            self.radar_preview.heading(column, text=column.upper())
        if sys.platform == "win32":
            self._schedule_auto()

    def _schedule_auto(self):
        if self._auto_id is None and sys.platform == "win32":
            self._auto_id = self.root.after(1500, self._scan_iq_option)

    def _auto_toggled(self):
        if self._auto_enabled.get():
            self._auto_paused = False
            self._auto_guard.reset()
            # Clear stopped automatic ROI so a reopened IQ Option can be found.
            if self._auto_region and not self.active:
                self.region = None
                self.window_target = None
                self._auto_region = False
                self.start_btn.configure(state="disabled")
            self.status.set("Procurando janela da IQ Option...")
        else:
            self._auto_paused = True
            self._auto_guard.reset()

    def _scan_iq_option(self):
        self._auto_id = None
        try:
            if (sys.platform != "win32" or not self._auto_enabled.get() or
                    self._auto_paused or self.active or self.region is not None or
                    self._picker is not None):
                return
            found = self._auto_guard.observe(enumerate_windows(), own_pid=os.getpid())
            if found is None:
                self.status.set("Procurando janela da IQ Option...")
                return
            region, window = found
            self._auto_region = True
            self.selected(region, window_target=window)
            self.start()
            self.status.set("IQ Option detectada · recorte automático em análise "
                            "(confirme as velas no painel)")
        except WindowCaptureError as exc:
            self.status.set(f"Detecção automática indisponível: {exc}")
        finally:
            self._schedule_auto()

    def toggle_details(self):
        self._details_open = not self._details_open
        if self._details_open:
            self.advanced_content.pack(fill="both", expand=True)
            self.details_toggle.configure(text="Ocultar detalhes  ▴")
            self._render_detail()
        else:
            self.advanced_content.pack_forget()
            self.details_toggle.configure(text="Ver explicação detalhada  ▾")

    def update_radar_preview(self, rows):
        """UI-only callback invoked by RadarTab's Tk poll, never by a worker."""
        self._radar_rows = tuple(rows)
        present = {row.symbol for row in self._radar_rows}
        for iid in self.radar_preview.get_children():
            if iid not in present:
                self.radar_preview.delete(iid)
        for row in self._radar_rows:
            values = (row.category, row.status, row.direction, row.last_closed)
            if self.radar_preview.exists(row.symbol):
                self.radar_preview.item(row.symbol, values=values)
            else:
                self.radar_preview.insert("", "end", iid=row.symbol,
                                          text=row.symbol, values=values)

    @staticmethod
    def _set_if_changed(variable, value):
        """Impede redesenho e callbacks de rastreamento para valores idênticos."""
        if variable.get() != value:
            variable.set(value)

    def _refresh_cycle_guard(self):
        # Captura WGC/mss só revela pixels. Nenhuma barra/quote entra na máquina
        # M1 com flags "confirmados" por inferência de imagem.
        status = self.m1_cycle.block_visual(self.timeframe.get())
        self.cycle_message.set(status.reason)
        if self.timeframe.get() != "M5":
            self.active_tracking.observe(None)
            self.active_context.set(
                f"{self.timeframe.get()} selecionado · AGUARDAR. "
                "O acompanhamento automático exige M5 no gráfico e no Monitor."
            )

    def _set_detail(self, text):
        if text == self._detail_cache:
            return
        self._detail_cache = text
        # Não repintar um campo de texto oculto a cada quadro do monitor.
        if self._details_open:
            self._render_detail()

    def _render_detail(self):
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", self._detail_cache or "")
        self.detail_text.configure(state="disabled")

    def _resize_preview(self, _event=None):
        if self.last_frame is None:
            return
        from PIL import Image, ImageTk
        available_w = self.image_label.winfo_width()
        available_h = self.image_label.winfo_height()
        if available_w < 80 or available_h < 80:
            return
        # Não converter o mesmo bitmap repetidamente sem mudança de tamanho.
        target_size = (available_w - 12, available_h - 12)
        if _event is not None and self._last_preview_size == target_size:
            return
        frame = self.last_frame.copy()
        frame.thumbnail(target_size, Image.Resampling.BILINEAR)
        self.preview_image = ImageTk.PhotoImage(frame)
        self._last_preview_size = target_size
        self._last_rendered_at = time.monotonic()
        self.image_label.configure(image=self.preview_image, text="")

    def _overlaps_selected_region(self):
        """Impede capturar o próprio DS Trader em vez da plataforma."""
        if self.region is None or not self.root.winfo_viewable():
            return False
        window = (self.root.winfo_rootx(), self.root.winfo_rooty(),
                  self.root.winfo_width(), self.root.winfo_height())
        return screen_region_is_obscured(self.region, window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self._picker = None

    def _cancel_selection(self):
        self._restore_window()
        self.status.set("Seleção cancelada. Nenhuma nova região foi capturada.")

    def select(self):
        if self.active:
            self.stop(user_requested=False)
        try:
            # Esconde o DS Trader antes de selecionar para não capturar a própria janela.
            self._picker = RegionPicker(
                self.root, self._selected_from_picker, on_cancel=self._cancel_selection
            )
            self.root.withdraw()
            self._picker.window.lift()
            self._picker.window.focus_force()
            self.status.set("Arraste sobre as velas na janela da IQ Option. Esc cancela.")
        except Exception as exc:
            self._restore_window()
            messagebox.showerror("Selecionar gráfico", str(exc), parent=self.root)

    def _selected_from_picker(self, region):
        # O overlay de selecao ja foi destruido e o app continua oculto.
        # Assim a ordem Z mostra a janela real por tras da selecao.
        try:
            target = select_window_for_region(region)
        except WindowCaptureError as exc:
            self._restore_window()
            self.region = None
            self.window_target = None
            self.start_btn.configure(state="disabled")
            self.status.set(str(exc))
            messagebox.showwarning("Fixar janela do grafico", str(exc), parent=self.root)
            return
        self._auto_region = False
        self._auto_enabled.set(False)
        self.selected(region, window_target=target)

    def selected(self, region, *, window_target: WindowTarget | None = None):
        self._restore_window()
        self.region = region
        self.window_target = window_target
        self.meta_text.set(
            f"{window_target.title[:32]} · {region.width}×{region.height} px"
            if window_target else f"{region.width} × {region.height} px"
        )
        self.status.set("Janela fixada · Clique em Iniciar análise" if window_target else
                        "Área escolhida · Clique em Iniciar análise")
        self.start_btn.configure(state="normal")
        self.last_frame = None
        self.preview_image = None
        self._last_preview_size = None
        self._last_rendered_at = 0.0
        self.image_label.configure(
            image="", text="Área selecionada.\n\nClique em Iniciar análise para acompanhar.")
        self.next_opinion.set("AGUARDAR")
        self.signal_subtitle.set("AGUARDANDO PRIMEIRA LEITURA")
        self.visual_bias.set("SEM VANTAGEM CLARA")
        self.visual_reason.set("Aguardando os primeiros candles reconhecidos.")
        self.speed_status.set("MOTOR PRONTO  ·  AGUARDANDO CAPTURA")
        self._refresh_cycle_guard()
        self._set_detail("Nenhuma imagem foi capturada ainda. "
                         "Mantenha a IQ Option visível ao lado do DS Trader.")

    def start(self):
        if self.active:
            return
        if self.region is None:
            messagebox.showinfo("DS Trader", "Selecione primeiro a região do gráfico.",
                                parent=self.root)
            return
        # No Windows não voltar silenciosamente a gravar o desktop inteiro.
        if sys.platform == "win32" and self.window_target is None:
            messagebox.showinfo("DS Trader", "Fixe primeiro a janela do grafico pelo botao.",
                                parent=self.root)
            return
        self.active_tracking.stop(wait=False)
        self.active_tracking = ActiveAssetTracking()
        self.active_tracking.configure_key(self._market_key_supplier())
        self.active_tracking.start()
        self.monitor = ScreenMonitor(self.region, interval_seconds=0.55,
                                     window_target=self.window_target)
        self.active = True
        self.pick_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.online_badge.configure(text="●  MONITORAMENTO ATIVO", fg=GREEN)
        self.preview_marker.configure(text="●  RECEBENDO IMAGENS", fg=CYAN)
        self.status.set("Captura da janela fixada iniciada" if self.window_target else
                        "Captura local iniciada")
        self._last_preview_at = time.monotonic()
        self._stale_notified = False
        self.monitor.start()
        self.poll()

    def set_market_key_supplier(self, supplier):
        """Supplier runs exclusively on Tk thread; provider work stays on worker."""
        self._market_key_supplier = supplier

    def _present(self, result):
        self.latest_assessment = result  # Tk thread, usado apenas pela tela Padrões
        score = score_visual(result)
        self._set_if_changed(self.confluence,
            (f"ALTA {score.alta}%  |  BAIXA {score.baixa}% · "
             f"{score.factors} grupos de critérios" if score else
             "AGUARDAR · critérios insuficientes ou sem ativo confirmado"))
        # Em captura WGC outras janelas na frente nao encobrem a origem.
        obscured = self.window_target is None and self._overlaps_selected_region()
        state = presentation_for(result, obscured=obscured)
        if result.identity_required:
            self._set_if_changed(
                self.meta_text,
                (f"{result.asset} · {result.asset_timeframe}"
                 + (" · OTC" if result.asset_otc else ""))
                if result.identity_confirmed else "Ativo não confirmado",
            )
        self.active_tracking.configure_key(self._market_key_supplier())
        self.active_tracking.observe(focus_identity(
            result, selected_timeframe=self.timeframe.get()))
        self._set_if_changed(self.next_opinion, state.side)
        self.signal_label.configure(fg=SIDE_COLORS[state.side])
        self.signal_context.configure(fg=SIDE_COLORS[state.side])
        self._set_if_changed(self.signal_subtitle, state.subtitle)
        self._set_if_changed(self.visual_bias, state.outlook)
        self._set_if_changed(self.visual_reason, state.outlook_reason)
        self.visual_bias_label.configure(
            fg=CYAN if state.outlook == "ALTA FAVORECIDA" else
               "#ffb166" if state.outlook == "BAIXA FAVORECIDA" else AMBER)
        self._set_if_changed(self.status, state.status)
        # O bloqueio temporal da IQ Option só muda ao selecionar período/
        # iniciar/parar; recalculá-lo em cada frame causava repinturas extras.
        self._set_if_changed(self.quality_status, "Gráfico encoberto" if obscured else
                             "Janela fixada; sem horário verificado"
                             if self.window_target and result.valid_roi else
                             "Recorte legível; sem horário verificado"
                             if result.valid_roi else "Leitura insuficiente")
        self._set_if_changed(self.pattern_text, state.pattern)
        self._set_if_changed(self.structure_text, state.structure)
        self._set_detail(state.detail)
        self._set_if_changed(self.observation, state.detail)
        self._set_if_changed(self.structures, state.structure)
        self._set_if_changed(
            self.speed_status,
            f"PROCESSAMENTO  {result.analysis_ms:.0f} ms   ·   "
            f"IDADE DO QUADRO  {result.capture_age_ms:.0f} ms   ·   "
            f"{result.detected} CANDLES",
        )
        try:
            ts = datetime.fromisoformat(result.captured_at).astimezone()
            local_time = ts.strftime("%H:%M:%S")
        except (TypeError, ValueError):
            local_time = "—"
        self._set_if_changed(self.last_update,
            f"Última captura: {local_time} (horário do PC)  ·  "
            f"{state.detected_label}  ·  {self.timeframe.get()} informado"
        )

    def _notify_stale(self):
        self.confluence.set("AGUARDAR · captura atrasada")
        self.latest_assessment = None
        self._stale_notified = True
        self.preview_marker.configure(text="●  LEITURA ATRASADA", fg=AMBER)
        self.next_opinion.set("AGUARDAR")
        self.signal_subtitle.set("Sem quadro recente · monitoramento atrasado")
        self.visual_bias.set("SEM DADOS RECENTES")
        self.visual_reason.set("A última imagem está atrasada; cenário suspenso.")
        self.visual_bias_label.configure(fg=AMBER)
        self.speed_status.set("SEM QUADRO RECENTE  ·  CAPTURA ATRASADA")
        self.active_tracking.observe(None)

    def poll(self):
        self.after_id = None
        if not self.active:
            return
        try:
            while True:
                item = self.monitor.results.get_nowait()
                if item[0] == "error":
                    self.stop(user_requested=False)
                    self.quality_status.set("Erro de captura")
                    self.status.set(item[1])
                    self._set_detail(item[1])
                    if self._auto_region:
                        self.region = None
                        self.window_target = None
                        self._auto_region = False
                        self._auto_guard.reset()
                        self.start_btn.configure(state="disabled")
                    return
                result, frame = item
                # Queue/poll delay is not included in the worker's age:
                # check age at the exact moment Tk is about to present it.
                if (result.stale_frame or
                    (result.capture_monotonic is not None and
                     time.monotonic() - result.capture_monotonic > 2.5)):
                    self._notify_stale()
                    continue
                self.last_frame = frame
                self._last_preview_size = None
                self._last_preview_at = time.monotonic()
                self._stale_notified = False
                # O estado textual responde a todo resultado; a miniatura
                # só precisa ser atualizada ~1 vez/s para poupar o Tkinter.
                if time.monotonic() - self._last_rendered_at >= .65:
                    self._resize_preview()
                self._present(result)
                self.preview_marker.configure(text="●  RECEBENDO IMAGENS", fg=CYAN)
        except Empty:
            pass
        for event in self.active_tracking.drain():
            self._set_if_changed(self.active_context, format_active_focus(event))
        latest_focus = self.active_tracking.current_status()
        if latest_focus is not None:
            self._set_if_changed(self.active_context, format_active_focus(latest_focus))
        if (self._last_preview_at is not None and not self._stale_notified and
                time.monotonic() - self._last_preview_at > 3.0):
            self._notify_stale()
        self.after_id = self.root.after(120, self.poll)

    def stop(self, *, user_requested=True):
        self.confluence.set("AGUARDAR · captura desligada")
        self.latest_assessment = None
        if user_requested:
            self._auto_paused = True
            self._auto_enabled.set(False)
        self.active = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.monitor is not None:
            self.monitor.stop(wait=False)
            self.monitor = None
        self.active_tracking.stop(wait=False)
        self.active_context.set("M5 · AGUARDAR. Monitor parado; nenhum par em acompanhamento.")
        self.pick_btn.configure(state="normal")
        self.start_btn.configure(state="normal" if self.region is not None else "disabled")
        self.stop_btn.configure(state="disabled")
        self.online_badge.configure(text="●  MONITORAMENTO DESLIGADO", fg=AMBER)
        self.preview_marker.configure(text="●  PAUSADO", fg=MUTED)
        self.next_opinion.set("AGUARDAR")
        self.visual_bias.set("SEM VANTAGEM CLARA")
        self.visual_reason.set("Monitoramento parado.")
        self.visual_bias_label.configure(fg=AMBER)
        self.speed_status.set("MONITOR PARADO  ·  SEM CAPTURA ATIVA")
        self.signal_label.configure(fg=AMBER)
        self.signal_context.configure(fg=AMBER)
        self.signal_subtitle.set("CAPTURA INTERROMPIDA")
        self._refresh_cycle_guard()
        self.status.set("Monitoramento parado")
        self.quality_status.set("Desconectado")
        self._set_detail("A captura foi interrompida. A última imagem pode "
                         "continuar na prévia, mas não há análise em andamento.")

    def shutdown(self):
        if self._auto_id is not None:
            self.root.after_cancel(self._auto_id)
            self._auto_id = None
        self.stop(user_requested=False)
