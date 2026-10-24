"""Painel de padrões a partir de leituras reais do monitor; sem feed fictício."""
from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from ds_trader.theme import BG, PANEL, PANEL_2, TEXT, MUTED, ACCENT

EDGE = "#23506a"
GREEN = "#1be0b6"
AMBER = "#ffbd5c"


@dataclass(frozen=True)
class PatternReading:
    state: str
    asset: str
    visual: str
    patterns: tuple[str, ...]
    structures: tuple[str, ...]
    reasons: tuple[str, ...]


def reading_for(result, *, active: bool) -> PatternReading:
    """Não converter pixels ou categorias em percentuais de ganho."""
    if not active or result is None or result.stale_frame or not result.valid_roi:
        return PatternReading("AGUARDAR", "Ativo não confirmado", "SEM DADOS SUFICIENTES",
                              (), (), ("Aguardando captura atual e legível.",))
    identity = (result.asset + (" (OTC)" if result.asset_otc else "")
                if result.identity_confirmed and result.asset else "Ativo não confirmado")
    direction = ("ALTA VISUAL" if result.next_visual_bias == "ALTA" else
                 "BAIXA VISUAL" if result.next_visual_bias == "BAIXA" else
                 "SEM VANTAGEM VISUAL")
    # O bloqueio da máquina de estados operacional continua independentemente
    # do que a direção estrutural dos pixels sugere.
    return PatternReading("VISUAL · NÃO VALIDADO", identity, direction,
                          tuple(result.patterns), tuple(result.structures),
                          tuple(result.visual_reasons))


def _label(parent, text="", *, color=TEXT, size=10, bold=False, variable=None, **kw):
    return tk.Label(parent, text=text, textvariable=variable,
                    bg=parent.cget("bg"), fg=color,
                    font=("Segoe UI", size, "bold" if bold else "normal"),
                    anchor="w", justify="left", **kw)


def _card(parent, title, text, *, tone=TEXT):
    card = tk.Frame(parent, bg=PANEL, highlightbackground=EDGE,
                    highlightthickness=1, padx=13, pady=11)
    _label(card, title, size=9, color=ACCENT, bold=True).pack(anchor="w")
    variable = tk.StringVar(value=text)
    _label(card, size=10, color=tone, variable=variable,
           wraplength=280).pack(anchor="w", pady=(7, 2))
    return card, variable


class PatternsTab:
    """Tela conectada ao último quadro do mesmo monitor; não inicia captura nova."""

    def __init__(self, parent, root, monitor):
        self.parent = parent
        self.root = root
        self.monitor = monitor
        self.photo = None
        self._last_frame = None
        self._last_size = None
        self._poll_id = None
        page = tk.Frame(parent, bg=BG, padx=14, pady=12)
        page.pack(fill="both", expand=True)
        _label(page, "PADRÕES E CONFLUÊNCIAS", size=20, bold=True).pack(anchor="w")
        _label(page, "Leitura visual da IQ Option · M5 · sem ordens, nem probabilidades inventadas",
               size=10, color=MUTED).pack(anchor="w", pady=(4, 12))

        workspace = tk.Frame(page, bg=BG)
        workspace.pack(fill="both", expand=True)
        workspace.grid_columnconfigure(0, weight=3)
        workspace.grid_columnconfigure(1, weight=2, minsize=315)
        workspace.grid_rowconfigure(0, weight=1)

        graph = tk.Frame(workspace, bg=PANEL, highlightbackground=EDGE,
                         highlightthickness=1, padx=10, pady=10)
        graph.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        _label(graph, "GRÁFICO DE ANÁLISE  •  MARCAÇÕES VISUAIS",
               size=10, color=ACCENT, bold=True).pack(anchor="w", pady=(0, 7))
        self.preview = tk.Label(graph, text="Aguardando gráfico capturado no Monitor",
                                bg="#061324", fg=MUTED, font=("Segoe UI", 12))
        self.preview.pack(fill="both", expand=True)
        self.preview.bind("<Configure>", lambda _event: self._refresh_preview(force=True))
        _label(graph, "Marcas relativas aos pixels; sem preço ou volume verificado na IQ Option.",
               size=9, color=MUTED).pack(anchor="w", pady=(8, 0))

        right = tk.Frame(workspace, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        intro, self.current = _card(right, "ATIVO EM ANÁLISE", "Aguardando captura")
        intro.pack(fill="x", pady=(0, 9))
        scenario, self.direction = _card(right, "CENÁRIO PARA PRÓXIMA VELA",
                                         "AGUARDAR · sem dados suficientes", tone=AMBER)
        scenario.pack(fill="x", pady=(0, 9))
        patterns, self.recognized = _card(right, "PADRÕES DE CANDLES",
                                          "Engolfo · Doji · Martelo: aguardando")
        patterns.pack(fill="x", pady=(0, 9))
        structures, self.zones = _card(right, "SUPORTE, RESISTÊNCIA E LINHAS",
                                       "Esperando estruturas reconhecidas")
        structures.pack(fill="x", pady=(0, 9))
        data, self.indicators = _card(right, "INDICADORES AVANÇADOS",
             "RSI, MACD, volume e Fibonacci em preço: indisponíveis sem OHLC verificado.")
        data.pack(fill="x", pady=(0, 9))

        bottom = tk.Frame(page, bg=PANEL, padx=14, pady=11,
                          highlightbackground=EDGE, highlightthickness=1)
        bottom.pack(fill="x", pady=(10, 0))
        _label(bottom, "RACIOCÍNIO VISUAL / VALIDAÇÃO", size=10,
               color=ACCENT, bold=True).pack(anchor="w", pady=(0, 5))
        self.reason = tk.StringVar(value="Inicie o Monitor para receber as leituras.")
        _label(bottom, variable=self.reason, size=9, color=TEXT, wraplength=1100,
               ).pack(anchor="w")
        _label(bottom, "Pontuação técnica (%): aguardando barras OHLC confirmadas. "
               "Não é possível calcular taxa de acerto pela captura de pixels.",
               size=9, color=AMBER).pack(anchor="w", pady=(6, 0))
        self._schedule()

    def _schedule(self):
        self._poll_id = self.root.after(1000, self.refresh)

    def _refresh_preview(self, *, force=False):
        # Reutiliza o quadro renderizado pela thread existente, sem OCR extra.
        frame = self.monitor.last_frame
        if frame is None or not self.monitor.active:
            self.preview.configure(image="", text="Aguardando imagem recente do Monitor")
            self.photo = None
            self._last_frame = None
            return
        size = (self.preview.winfo_width() - 14, self.preview.winfo_height() - 14)
        if size[0] < 120 or size[1] < 120:
            return
        if not force and self._last_frame is frame and size == self._last_size:
            return
        from PIL import Image, ImageTk
        resized = frame.copy()
        resized.thumbnail(size, Image.Resampling.BILINEAR)
        self.photo = ImageTk.PhotoImage(resized)
        self.preview.configure(image=self.photo, text="")
        self._last_size = size
        self._last_frame = frame

    def refresh(self):
        self._poll_id = None
        if not self.parent.winfo_exists():
            return
        if self.parent.winfo_ismapped():
            reading = reading_for(self.monitor.latest_assessment,
                                  active=self.monitor.active)
            self.current.set(reading.asset + " · " + reading.state)
            self.direction.set(reading.visual + "\nOperação: AGUARDAR até validação temporal.")
            recognized = ", ".join(reading.patterns) if reading.patterns else "Não confirmados"
            self.recognized.set("Engolfo / Doji / Martelo: " + recognized)
            self.zones.set(", ".join(reading.structures) if reading.structures
                           else "Suporte, resistência, LTA/LTB: sem estruturas validadas")
            self.reason.set(" · ".join(reading.reasons[:4]) or
                            "Não há confluência visual suficiente.")
            self._refresh_preview()
        self._schedule()

    def shutdown(self):
        if self._poll_id is not None:
            self.root.after_cancel(self._poll_id)
            self._poll_id = None
