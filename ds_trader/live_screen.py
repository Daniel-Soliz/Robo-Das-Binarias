"""Monitoramento visual LOCAL da tela. Nao fornece preco, horario de mercado nem sinais de ordens."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from queue import Empty, Full, Queue
import threading
import time
from statistics import median
from ds_trader.next_candle import evaluate_next
from ds_trader.window_capture import WindowTarget, WindowCaptureError, check_target_window

# Nao importar PIL/mss no modulo: CSV e testes funcionam sem captura.

@dataclass(frozen=True)
class Region:
    left: int
    top: int
    width: int
    height: int

    def __post_init__(self):
        if any(type(v) is not int for v in (self.left, self.top, self.width, self.height)):
            raise ValueError("Coordenadas devem ser numeros inteiros")
        if not (180 <= self.width <= 8000 and 120 <= self.height <= 5000):
            raise ValueError("Selecione somente uma area do grafico (minimo 180x120)")

    def mss_rect(self):
        return dict(left=self.left, top=self.top, width=self.width, height=self.height)


@dataclass(frozen=True)
class VisualCandle:
    x: int
    high: float
    low: float
    open: float
    close: float
    direction: str


@dataclass(frozen=True)
class Assessment:
    captured_at: str
    detected: int
    completed_estimate: int
    movement: str
    explanation: str
    is_market_quote: bool = False
    trading_signal: bool = False
    bias: str = "AGUARDAR"
    patterns: tuple[str, ...] = ()
    structures: tuple[str, ...] = ()
    valid_roi: bool = False
    temporal_verified: bool = False
    candle_xs: tuple[int, ...] = ()
    model_width: int = 1
    lta: tuple[float, float] | None = None
    ltb: tuple[float, float] | None = None


def detect_visual_candles(image):
    """Heuristica sobre PIXELS HSV; nao converte coordenadas em preco ou OHLC de corretora.

    Funciona apenas para paletas de velas verde/vermelho com corpos separados.
    Nao reconhecer visualmente NAO e evidencia de mercado lateral.
    """
    if image.width < 180 or image.height < 120:
        return ()
    source = image.copy()
    source.thumbnail((1200, 700))
    hsv = source.convert("HSV")
    px = hsv.load()
    width, height = hsv.size
    labels = []
    # As cores de grade/cursos podem impedir deteccao. Resultado sempre aproximado.
    for x in range(width):
        up = down = 0
        for y in range(4, height - 4, 2):
            h, s, v = px[x, y]
            if s < 92 or v < 78:
                continue
            if 51 <= h <= 124:
                up += 1
            elif h <= 11 or h >= 246:
                down += 1
        if up >= 3 and up >= 3 * down:
            labels.append("ALTA")
        elif down >= 3 and down >= 3 * up:
            labels.append("BAIXA")
        else:
            labels.append(None)
    groups = []
    begin = 0
    color = None
    for x in range(width + 1):
        next_color = labels[x] if x < width else None
        if next_color != color:
            if color is not None and x - begin >= 3:
                groups.append((begin, x, color))
            begin = x
            color = next_color
    candles = []
    for a, b, direction in groups:
        span = b - a
        if span > max(18, int(width * .055)):
            continue
        rows = []
        for y in range(4, height - 4):
            count = 0
            for x in range(a, b):
                h, s, v = px[x, y]
                if s >= 92 and v >= 78 and ((51 <= h <= 124) if direction == "ALTA" else (h <= 11 or h >= 246)):
                    count += 1
            rows.append(count)
        colored = [i for i, n in enumerate(rows) if n > 0]
        body = [i for i, n in enumerate(rows) if n >= max(2, int(span * .6))]
        if len(colored) < 5 or len(body) < 2:
            continue
        top = min(body) + 4
        bottom = max(body) + 4
        high = 1.0 - (min(colored) + 4) / height
        low = 1.0 - (max(colored) + 4) / height
        if high < low or top >= bottom:
            continue
        open_ = 1.0 - (bottom if direction == "ALTA" else top) / height
        close = 1.0 - (top if direction == "ALTA" else bottom) / height
        candles.append(VisualCandle((a + b) // 2, high, low, open_, close, direction))
    return tuple(candles)


def _roi_quality(detected, width):
    """Verifica regularidade geométrica da seleção, sem fingir precisão de preço.

    Grandes irregularidades são típicas de menus, botões ou pixels isolados.
    É um filtro conservador, não certificação de reconhecimento.
    """
    if len(detected) < 26:
        return False, "Necessarios pelo menos 26 corpos de vela reconhecidos em uma unica regiao."
    gaps=[b.x-a.x for a,b in zip(detected,detected[1:])]
    if any(g<=2 for g in gaps):
        return False,"Velas mescladas: aumente o zoom do grafico."
    step=median(gaps)
    consistent=sum(.65*step<=g<=1.35*step for g in gaps)/len(gaps)
    if not (4<=step<=90) or consistent<.80:
        return False,"Espacamento irregular: selecione somente a area do grafico, sem menus ou botoes."
    if detected[-1].x-detected[0].x<width*.28:
        return False,"Regiao nao parece conter um grafico amplo de candles."
    return True, ""


def assess(image, captured_at=None):
    """Hipotese visual nao auditavel; sem dados temporais/ordens da corretora."""
    when = captured_at or datetime.now(timezone.utc).isoformat()
    detected=detect_visual_candles(image)
    completed=detected[:-1]  # vela mais à direita pode estar em formação
    scaled=image.copy()
    scaled.thumbnail((1200,700))
    roi_ok, why = _roi_quality(detected, scaled.width)
    bias="AGUARDAR"
    patterns=()
    structures=()
    lta=ltb=None
    if not roi_ok:
        movement="Leitura insuficiente"
        explanation=(f"{len(detected)} possiveis corpos coloridos identificados. "
                     f"{why} Nao existe hipotese segura para a proxima vela.")
    else:
        past=completed[-8:-5]
        recent=completed[-3:]
        delta=sum(c.close for c in recent)/3-sum(c.close for c in past)/3
        movement=("Alta visual relativa" if delta>.018 else
                  "Baixa visual relativa" if delta<-.018 else
                  "Movimento visual indefinido")
        # Excluir a ultima figura nao COMPROVA fechamento das anteriores.
        # Preserva a descricao de estruturas, mas bloqueia vies CALL/PUT.
        opinion=evaluate_next(completed,source="screen",closed_confirmed=False)
        lta,ltb=opinion.lta,opinion.ltb
        bias=opinion.side
        patterns=opinion.patterns
        structures=tuple(x for x,found in (
            ("LTA por fundos ascendentes",opinion.lta),
            ("LTB por topos descendentes",opinion.ltb),
            ("Suporte relativo",opinion.support is not None),
            ("Resistencia relativa",opinion.resistance is not None)
        ) if found)
        explanation=(f"{len(completed)} corpos de velas anteriores estimados. "
                     f"{movement}. Padroes: {', '.join(patterns) or 'nenhum confirmado'}. "
                     f"Estruturas: {', '.join(structures) or 'insuficientes'}. "
                     + " ".join(opinion.reasons[-3:])+
                     " ATENCAO: hipotese apenas visual, sem comprovacao do fechamento, "
                     "hora da proxima vela, cotacao ou vencimento; NAO e sinal validado.")
    return Assessment(when,len(detected),len(completed),movement,explanation,
                      bias=bias,patterns=patterns,structures=structures,valid_roi=roi_ok,
                      candle_xs=tuple(c.x for c in completed),model_width=scaled.width,
                      lta=lta,ltb=ltb)


def annotate_preview(frame, result):
    """Linhas relativas de LTA/LTB na previa; nao altera a captura original."""
    if not result.valid_roi or len(result.candle_xs)<15:
        return frame
    from PIL import ImageDraw
    canvas=frame.copy()
    draw=ImageDraw.Draw(canvas)
    xs=result.candle_xs
    scale_x=canvas.width/max(1,result.model_width)
    for line,color,name in ((result.lta,"#38c6fa","LTA"),
                            (result.ltb,"#ffb166","LTB")):
        if not line:
            continue
        n=min(14,len(xs)-1)
        slope=line[1]-line[0]
        earlier=line[1]-n*slope
        start=(int(xs[-1-n]*scale_x),round((1-earlier)*canvas.height))
        finish=(int(xs[-1]*scale_x),round((1-line[1])*canvas.height))
        if not all(-canvas.height<=v<=canvas.height*2 for v in (start[1],finish[1])):
            continue
        draw.line((start,finish),fill=color,width=3)
        draw.text((max(1,finish[0]-38),max(2,min(canvas.height-18,finish[1]-20))),
                  name,fill=color)
    return canvas


def crop_window_image(frame, target: WindowTarget):
    """Recorte relativo a janela, imune a movimento/oclusao no desktop."""
    left, top, right, bottom = target.bounds
    if right <= left or bottom <= top or frame.width < 180 or frame.height < 120:
        raise WindowCaptureError("Quadro da janela sem dimensoes validas.")
    sx = frame.width / (right - left)
    sy = frame.height / (bottom - top)
    if abs(sx - sy) > max(sx, sy) * .12:
        raise WindowCaptureError("A proporcao da janela mudou. Selecione o grafico novamente.")
    x0, y0, x1, y1 = target.crop
    box = (round(x0 * sx), round(y0 * sy), round(x1 * sx), round(y1 * sy))
    if (box[0] < 0 or box[1] < 0 or box[2] > frame.width or
            box[3] > frame.height or box[2] - box[0] < 180 or
            box[3] - box[1] < 120):
        raise WindowCaptureError("Recorte saiu dos limites da janela. Selecione novamente.")
    return frame.crop(box)



class ScreenMonitor:
    """Captura sob acao explicita do usuario; threads nao acessam widgets Tk.

    Entrega imagem em memoria e avaliacao em fila de capacidade 1. Nenhum frame
    e salvo em disco, transmitido ou enviado para a corretora.
    """
    def __init__(self, region: Region, interval_seconds: float = 1.2,
                 window_target: WindowTarget | None = None):
        if not (0.5 <= interval_seconds <= 10):
            raise ValueError("Intervalo de atualizacao invalido")
        self.region = region
        self.window_target = window_target
        self.interval_seconds = interval_seconds
        self.results = Queue(maxsize=1)
        self._stop = threading.Event()
        self._thread = None
        self._last_signature = None
        self._stable_reads = 0

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._stable_reads=0
        self._last_signature=None
        self._thread = threading.Thread(target=self._run, daemon=True, name="ds-screen-read-only")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread is not None and threading.current_thread() is not self._thread:
            self._thread.join(timeout=3)

    def _emit(self, data):
        try:
            self.results.put_nowait(data)
        except Full:
            try:
                self.results.get_nowait()
            except Empty:
                pass
            self.results.put_nowait(data)

    def _run(self):
        try:
            if self.window_target is not None:
                self._run_window()
            else:
                self._run_desktop()
        except Exception as exc:
            # Nao registra pixels, janela, titulo ou dados de conta.
            self._emit(("error", f"Captura interrompida: {type(exc).__name__}: {exc}"))

    def _process_frame(self, frame):
        result = assess(frame)
        if result.valid_roi and len(result.candle_xs)>5:
            gaps=[b-a for a,b in zip(result.candle_xs,result.candle_xs[1:])]
            step=median(gaps)
            signature=(result.detected,round(step),
                       round(result.candle_xs[-1]/max(1,step/2)))
            if signature==self._last_signature:
                self._stable_reads+=1
            else:
                self._last_signature=signature
                self._stable_reads=1
            if self._stable_reads<3:
                result=replace(
                    result,bias="AGUARDAR",
                    explanation=result.explanation+
                    " Aguardando tres leituras geometricamente estaveis."
                )
        else:
            self._last_signature=None
            self._stable_reads=0
        frame.thumbnail((1050, 590))
        frame=annotate_preview(frame,result)
        self._emit((result, frame))

    def _run_desktop(self):
        """Legado: captura de desktop somente para testes/modo sem janela."""
        from mss import mss
        from PIL import Image
        with mss() as capture:
            virtual = capture.monitors[0]
            r = self.region
            if (r.left < virtual["left"] or r.top < virtual["top"] or
                r.left + r.width > virtual["left"] + virtual["width"] or
                r.top + r.height > virtual["top"] + virtual["height"]):
                raise ValueError("A area selecionada ultrapassa a tela disponivel")
            while not self._stop.is_set():
                began = time.monotonic()
                shot = capture.grab(r.mss_rect())
                frame = Image.frombytes("RGB", shot.size, shot.rgb)
                self._process_frame(frame)
                self._stop.wait(max(0, self.interval_seconds - (time.monotonic() - began)))

    def _run_window(self):
        """Windows Graphics Capture: pega o HWND, nao pixels de janelas por cima."""
        from PIL import Image
        try:
            from windows_capture import WindowsCapture
        except ImportError as exc:
            raise WindowCaptureError("Modulo windows-capture ausente no instalador.") from exc
        target = self.window_target
        check_target_window(target)
        capture = WindowsCapture(window_hwnd=target.hwnd, cursor_capture=False,
                                 draw_border=None,
                                 minimum_update_interval=int(self.interval_seconds*1000))
        closed = threading.Event()
        failed = threading.Event()
        last_frame = [time.monotonic()]

        @capture.event
        def on_frame_arrived(frame, capture_control):
            if self._stop.is_set():
                capture_control.stop()
                return
            try:
                check_target_window(target)
                # Frame WGC e BGRA. A copia e feita ENQUANTO o buffer esta vivo.
                picture = Image.frombytes("RGB", (frame.width, frame.height),
                                          frame.frame_buffer.tobytes(), "raw", "BGRX")
                cut = crop_window_image(picture, target)
                last_frame[0] = time.monotonic()
                self._process_frame(cut)
            except Exception as exc:
                self._emit(("error", f"Falha na janela fixada: {type(exc).__name__}: {exc}"))
                failed.set()
                capture_control.stop()

        @capture.event
        def on_closed():
            closed.set()

        controller = capture.start_free_threaded()
        try:
            while not self._stop.wait(.5) and not failed.is_set():
                check_target_window(target)
                if closed.is_set() or controller.is_finished():
                    raise WindowCaptureError("A captura da janela foi encerrada. Selecione novamente.")
                if time.monotonic() - last_frame[0] > 12:
                    raise WindowCaptureError("A janela deixou de fornecer quadros novos; "
                                             "restaure e confira o grafico antes de continuar.")
        finally:
            controller.stop()
