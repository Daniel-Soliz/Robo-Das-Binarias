"""Monitoramento visual LOCAL da tela. Nao fornece preco, horario de mercado nem sinais de ordens."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from queue import Empty, Full, Queue
import threading
import time
from statistics import median
from ds_trader.next_candle import evaluate_next
from ds_trader.visual_outlook import compare_visual_scenarios
from ds_trader.window_capture import WindowTarget, WindowCaptureError, check_target_window
from ds_trader.asset_identity import IdentityGuard, parse_asset_header

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
    support_rel: float | None = None
    resistance_rel: float | None = None
    trend_visual: str = "INDEFINIDA"
    next_visual_bias: str = "INDEFINIDO"
    visual_reasons: tuple[str, ...] = ()
    recent_top_rel: float | None = None
    recent_bottom_rel: float | None = None
    analysis_ms: float = 0.0
    capture_age_ms: float = 0.0
    asset: str = ""
    asset_timeframe: str = ""
    asset_otc: bool = False
    identity_confirmed: bool = False
    identity_required: bool = False
    identity_generation: int = 0
    identity_reason: str = "Sem identificação do ativo"
    capture_monotonic: float | None = None
    stale_frame: bool = False


def detect_visual_candles(image):
    """Heuristica sobre PIXELS HSV; nao converte coordenadas em preco ou OHLC de corretora.

    Funciona apenas para paletas de velas verde/vermelho com corpos separados.
    Nao reconhecer visualmente NAO e evidencia de mercado lateral.
    """
    if image.width < 180 or image.height < 120:
        return ()
    # Converter diretamente quando já cabe no detector; copiar somente
    # imagens grandes para limitar o custo da matriz HSV.
    source = image
    if image.width > 1200 or image.height > 700:
        source = image.copy()
        source.thumbnail((1200, 700))
    hsv = source.convert("HSV")
    # NumPy acelera a contagem de pixels e corpos inteiros no Windows.
    # O detector Python continua disponivel para testes e ambientes sem NumPy.
    try:
        from ds_trader.visual_fast import detect_numpy
        return detect_numpy(hsv, VisualCandle)
    except ImportError:
        pass
    px = hsv.load()
    width, height = hsv.size
    # Desconsidera linhas horizontais vermelhas/verdes que atravessam o
    # grafico e seriam confundidas com velas no caminho sem NumPy.
    excluded_rows = set()
    for y in range(4, height - 4):
        red = green = 0
        for x in range(width):
            h, s, v = px[x, y]
            if s < 92 or v < 78:
                continue
            if 51 <= h <= 124:
                green += 1
            elif h <= 11 or h >= 246:
                red += 1
        if max(red, green) > width * .55:
            excluded_rows.add(y)
    labels = []
    # As cores de grade/cursos podem impedir deteccao. Resultado sempre aproximado.
    for x in range(width):
        up = down = 0
        for y in range(4, height - 4, 2):
            if y in excluded_rows:
                continue
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
            if y in excluded_rows:
                rows.append(0)
                continue
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


def _model_width(image):
    """Largura de pixels no detector após thumbnail (sem cópia extra)."""
    factor = min(1.0, 1200 / image.width, 700 / image.height)
    return max(1, round(image.width * factor))


def assess(image, captured_at=None):
    """Hipotese visual nao auditavel; sem dados temporais/ordens da corretora."""
    when = captured_at or datetime.now(timezone.utc).isoformat()
    detected=detect_visual_candles(image)
    completed=detected[:-1]  # vela mais à direita pode estar em formação
    # O detector limita o tamanho, sem recriar outra miniatura por frame.
    roi_ok, why = _roi_quality(detected, _model_width(image))
    bias="AGUARDAR"
    patterns=()
    structures=()
    lta=ltb=None
    support_rel=resistance_rel=None
    trend_visual="INDEFINIDA"
    next_visual_bias="INDEFINIDO"
    visual_reasons=()
    recent_top_rel=recent_bottom_rel=None
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
        support_rel,resistance_rel=opinion.support,opinion.resistance
        trend_visual=opinion.trend
        outlook=compare_visual_scenarios(completed,opinion)
        next_visual_bias=outlook.direction
        visual_reasons=outlook.reasons
        recent_top_rel=outlook.recent_top
        recent_bottom_rel=outlook.recent_bottom
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
                     f"Cenario visual da proxima vela: {next_visual_bias}. "
                     f"Motivos: {'; '.join(visual_reasons)}. "
                     + " ".join(opinion.reasons[-3:])+
                     " ATENCAO: hipotese apenas visual, sem comprovacao do fechamento, "
                     "hora da proxima vela, cotacao ou vencimento; NAO e sinal validado.")
    return Assessment(when,len(detected),len(completed),movement,explanation,
                      bias=bias,patterns=patterns,structures=structures,valid_roi=roi_ok,
                      candle_xs=tuple(c.x for c in completed),
                      model_width=_model_width(image),
                      lta=lta,ltb=ltb,support_rel=support_rel,
                      resistance_rel=resistance_rel,trend_visual=trend_visual,
                      next_visual_bias=next_visual_bias,visual_reasons=visual_reasons,
                      recent_top_rel=recent_top_rel,recent_bottom_rel=recent_bottom_rel)


def annotate_preview(frame, result):
    """LTA/LTB e niveis relativos na previa; nunca inventa precos de mercado."""
    if not result.valid_roi or len(result.candle_xs)<15:
        return frame
    from PIL import ImageDraw
    canvas=frame.copy()
    draw=ImageDraw.Draw(canvas)
    xs=result.candle_xs
    scale_x=canvas.width/max(1,result.model_width)
    for level, color, label in (
        (result.support_rel if result.support_rel is not None else result.recent_bottom_rel,
         "#44d4b0", "SUPORTE VISUAL" if result.support_rel is not None else "FUNDO RECENTE"),
        (result.resistance_rel if result.resistance_rel is not None else result.recent_top_rel,
         "#f7b354", "RESIST. VISUAL" if result.resistance_rel is not None else "TOPO RECENTE"),
    ):
        if level is None or not 0 <= level <= 1:
            continue
        y=round((1-level)*canvas.height)
        if not 12 <= y < canvas.height-12:
            continue
        draw.line((0,y,canvas.width-1,y),fill=color,width=2)
        # Rotulos identificam posicoes aproximadas na imagem, nao cotacoes.
        draw.rectangle((4,max(1,y-17),132,max(1,y-2)),fill="#152334")
        draw.text((7,max(1,y-16)),label,fill=color)
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


def read_window_header(image, target):
    """Best-effort optional LOCAL OCR; unavailable engine means unknown.

    Never read an IQ Option account, files or remote services. Crop only the
    header above the user-selected candle region. OCR failure is not evidence.
    """
    from PIL import ImageOps
    try:
        import pytesseract
    except ImportError:
        return ""
    from ds_trader.ocr_runtime import configure_tesseract
    configure_tesseract(pytesseract)
    header_bottom = min(image.height, max(45, target.crop[1]))
    strip = image.crop((0, 0, image.width, header_bottom))
    strip = ImageOps.autocontrast(strip.convert("L"))
    if strip.width < 1400:
        strip = strip.resize((strip.width * 2, strip.height * 2))
    try:
        return pytesseract.image_to_string(strip, config="--psm 6", timeout=.8)
    except (OSError, RuntimeError):
        # OCR/Tesseract may not be installed; do not pretend identity confirmed.
        return ""


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
                 window_target: WindowTarget | None = None, header_reader=None):
        if not (0.5 <= interval_seconds <= 10):
            raise ValueError("Intervalo de atualizacao invalido")
        self.region = region
        self.window_target = window_target
        self.interval_seconds = interval_seconds
        self.results = Queue(maxsize=1)
        # A captura recebe pixels sem aguardar a análise. Mantém só o quadro
        # mais novo para não acumular latência durante movimentos rápidos.
        self._frames = Queue(maxsize=1)
        self._stop = threading.Event()
        self._thread = None
        self._last_signature = None
        self._stable_reads = 0
        self._identity = IdentityGuard()
        self._frame_id = 0
        self._last_processed_frame_id = -1
        self._header_reader = header_reader or read_window_header

    @property
    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.running:
            return
        self._stop.clear()
        self._stable_reads=0
        self._last_signature=None
        self._identity = IdentityGuard()
        self._frame_id = 0
        self._last_processed_frame_id = -1
        self._thread = threading.Thread(target=self._run, daemon=True, name="ds-screen-read-only")
        self._thread.start()

    def stop(self, *, wait=True):
        """Na interface não bloquear o thread principal esperando callback WGC."""
        self._stop.set()
        if wait and self._thread is not None and threading.current_thread() is not self._thread:
            self._thread.join(timeout=3)

    @staticmethod
    def _put_latest(queue, data):
        try:
            queue.put_nowait(data)
        except Full:
            try:
                queue.get_nowait()
            except Empty:
                pass
            try:
                queue.put_nowait(data)
            except Full:
                pass  # múltiplos callbacks simultâneos: vence o mais recente

    def _emit(self, data):
        self._put_latest(self.results, data)

    def _run(self):
        try:
            if self.window_target is not None:
                self._run_window()
            else:
                self._run_desktop()
        except Exception as exc:
            # Nao registra pixels, janela, titulo ou dados de conta.
            self._emit(("error", f"Captura interrompida: {type(exc).__name__}: {exc}"))

    def _process_frame(self, frame, captured_at_mono=None, *, header_text=None, frame_id=None):
        if self.window_target is not None:
            if frame_id is None:
                self._frame_id += 1
                frame_id = self._frame_id
            if frame_id <= self._last_processed_frame_id:
                return  # old callback/job can never publish under a newer asset
            self._last_processed_frame_id = frame_id
        started = time.perf_counter()
        result = assess(frame)
        preliminary_age = ((time.monotonic() - captured_at_mono) * 1000
                           if captured_at_mono is not None else 0)
        stale_frame = preliminary_age > 2500
        if self.window_target is not None:
            # Each frame must carry its OWN header observation. Unread/late
            # frames cannot inherit identity confirmed for previous pixels.
            candidate = None if stale_frame else parse_asset_header(header_text)
            identity = self._identity.observe(candidate, frame_id=frame_id)
            if identity.changed:
                self._last_signature = None
                self._stable_reads = 0
            if not identity.confirmed:
                result = replace(result, bias="AGUARDAR", next_visual_bias="INDEFINIDO",
                                 visual_reasons=(), identity_reason=identity.reason,
                                 explanation=result.explanation + " " + identity.reason)
            else:
                current = identity.current
                result = replace(result, asset=current.symbol,
                                 asset_timeframe=current.timeframe,
                                 asset_otc=current.otc, identity_confirmed=True,
                                 identity_reason=identity.reason)
            result = replace(result, identity_generation=identity.generation,
                             identity_required=True)
        if stale_frame:
            result = replace(result, bias="AGUARDAR", next_visual_bias="INDEFINIDO",
                             identity_confirmed=False, asset="", visual_reasons=(),
                             identity_reason="Quadro capturado há mais de 2,5 segundos",
                             explanation=result.explanation + " Quadro atrasado; análise suspensa.")
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
        # Prévia suficiente para a coluna de ~700px; menor custo de
        # redimensionar/copiar entre worker e Tk.
        frame.thumbnail((880, 510))
        frame=annotate_preview(frame,result)
        elapsed = max(0.0, (time.perf_counter() - started) * 1000)
        age = (max(0.0, (time.monotonic() - captured_at_mono) * 1000)
               if captured_at_mono is not None else 0.0)
        result = replace(result, analysis_ms=round(elapsed, 1),
                         capture_age_ms=round(age, 1),
                         capture_monotonic=captured_at_mono,
                         stale_frame=stale_frame or age > 2500)
        if age > 2500 and not stale_frame:
            result = replace(result, bias="AGUARDAR", next_visual_bias="INDEFINIDO",
                             identity_confirmed=False, asset="", visual_reasons=(),
                             identity_reason="Quadro atrasado após processamento")
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
                captured = time.monotonic()
                frame = Image.frombytes("RGB", shot.size, shot.rgb)
                self._process_frame(frame, captured)
                self._stop.wait(max(0, self.interval_seconds - (time.monotonic() - began)))

    def _consume_window_frames(self, target, failed):
        """Trabalho pesado fica nesta thread, nunca no callback do WGC."""
        from PIL import Image
        while not self._stop.is_set() and not failed.is_set():
            try:
                width, height, raw, captured = self._frames.get(timeout=.15)
            except Empty:
                continue
            try:
                picture = Image.frombytes("RGB", (width, height), raw, "raw", "BGRX")
                cut = crop_window_image(picture, target)
                # OCR on this *same* captured frame; skipping it and reusing
                # an older header can associate a different chart with old asset.
                header = self._header_reader(picture, target)
                if not self._stop.is_set():
                    self._process_frame(cut, captured, header_text=header)
            except Exception as exc:
                failed.set()
                self._emit(("error", f"Falha ao processar quadro: {type(exc).__name__}: {exc}"))
                break

    def _run_window(self):
        """WGC só copia o buffer na thread de captura; análise não bloqueia WGC."""
        try:
            from windows_capture import WindowsCapture
        except ImportError as exc:
            raise WindowCaptureError("Modulo windows-capture ausente no instalador.") from exc
        target = self.window_target
        check_target_window(target)
        capture = WindowsCapture(
            window_hwnd=target.hwnd, cursor_capture=False, draw_border=None,
            minimum_update_interval=int(self.interval_seconds * 1000))
        closed = threading.Event()
        failed = threading.Event()
        last_frame = [time.monotonic()]
        last_offer = [0.0]
        worker = threading.Thread(
            target=self._consume_window_frames, args=(target, failed),
            name="ds-frame-analyzer", daemon=True)
        worker.start()

        @capture.event
        def on_frame_arrived(frame, capture_control):
            if self._stop.is_set() or failed.is_set():
                capture_control.stop()
                return
            current = time.monotonic()
            if current - last_offer[0] < self.interval_seconds * .9:
                return
            try:
                # A cópia é obrigatória enquanto o buffer nativo está vivo.
                # Conversão PIL, ROI, candles e linhas ficam na outra thread.
                raw = frame.frame_buffer.tobytes()
                last_offer[0] = current
                last_frame[0] = current
                self._put_latest(self._frames, (frame.width, frame.height, raw, current))
            except Exception as exc:
                self._emit(("error", f"Falha na captura WGC: {type(exc).__name__}: {exc}"))
                failed.set()
                capture_control.stop()

        @capture.event
        def on_closed():
            closed.set()

        try:
            controller = capture.start_free_threaded()
        except Exception:
            failed.set()
            worker.join(timeout=.5)
            raise
        try:
            while not self._stop.wait(.4) and not failed.is_set():
                check_target_window(target)
                if closed.is_set() or controller.is_finished():
                    raise WindowCaptureError("A captura da janela foi encerrada. Selecione novamente.")
                if time.monotonic() - last_frame[0] > 12:
                    raise WindowCaptureError(
                        "A janela deixou de fornecer quadros novos; "
                        "restaure e confira o grafico antes de continuar.")
        finally:
            failed.set()
            controller.stop()
            worker.join(timeout=.8)
