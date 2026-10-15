"""Fonte principal: lê apenas os pixels da tela, sem interagir com a plataforma."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

import cv2
import numpy as np

from config import Configuracao
from data_sources.base import Amostra, AoReceber, Candle, DataSource, EstadoFonte
from utils.ocr import extrair_texto, identificar_cabecalho

LOG = logging.getLogger(__name__)


def extrair_velas(
    imagem_bgr: np.ndarray, timeframe: str
) -> tuple[Candle, ...]:
    """Estima OHLC relativo pelo corpo/pavio coloridos visíveis.

    Usa eixos normalizados no sentido do preço (maior y visual = menor preço).
    A captura não fornece o timestamp histórico nem o preço real, portanto
    instante=None e preco_real=False. Requer velas separadas horizontalmente.
    """
    if imagem_bgr.ndim != 3 or imagem_bgr.shape[2] != 3:
        raise ValueError("Imagem do gráfico deve estar em BGR.")
    altura, largura = imagem_bgr.shape[:2]
    if altura < 30 or largura < 50:
        return ()
    hsv = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2HSV)
    # Limites ajustáveis futuramente pela calibração de cores.
    verde = cv2.inRange(hsv, (35, 65, 65), (90, 255, 255))
    vermelho_a = cv2.inRange(hsv, (0, 65, 65), (12, 255, 255))
    vermelho_b = cv2.inRange(hsv, (168, 65, 65), (179, 255, 255))
    vermelho = cv2.bitwise_or(vermelho_a, vermelho_b)
    mascara = cv2.bitwise_or(verde, vermelho)
    # Exclui pequenas manchas e separa grupos de colunas.
    colunas = (np.count_nonzero(mascara, axis=0) >= 3).astype(np.uint8)
    comeco: int | None = None
    grupos: list[tuple[int, int]] = []
    for x, preenchida in enumerate(np.r_[colunas, 0]):
        if preenchida and comeco is None:
            comeco = x
        elif not preenchida and comeco is not None:
            if x - comeco >= 2:
                grupos.append((comeco, x))
            comeco = None

    def normalizar(y: int) -> float:
        return max(0.0, min(1.0, 1.0 - y / (altura - 1)))

    candles: list[Candle] = []
    for inicio, fim in grupos:
        trecho = mascara[:, inicio:fim] > 0
        y_indices, _ = np.where(trecho)
        if len(y_indices) < 8:
            continue
        # Corpo: linhas em que vários pixels coloridos coexistem.
        largura_grupo = fim - inicio
        preenchimento = np.count_nonzero(trecho, axis=1)
        minimo_corpo = max(2, int(np.ceil(largura_grupo * 0.55)))
        corpo = np.where(preenchimento >= minimo_corpo)[0]
        if len(corpo) < 2 or corpo[-1] - corpo[0] < 1:
            continue
        # Predominância de cor no corpo; pixels misturados são rejeitados.
        area = (slice(int(corpo[0]), int(corpo[-1]) + 1), slice(inicio, fim))
        verdes = int(np.count_nonzero(verde[area]))
        vermelhos = int(np.count_nonzero(vermelho[area]))
        if min(verdes, vermelhos) > max(verdes, vermelhos) * 0.25:
            continue
        alta = verdes > vermelhos
        topo_corpo, fundo_corpo = int(corpo[0]), int(corpo[-1])
        maxima, minima = normalizar(int(y_indices.min())), normalizar(int(y_indices.max()))
        abertura = normalizar(fundo_corpo if alta else topo_corpo)
        fechamento = normalizar(topo_corpo if alta else fundo_corpo)
        candles.append(
            Candle(
                instante=None,
                abertura=abertura,
                maxima=maxima,
                minima=minima,
                fechamento=fechamento,
                timeframe=timeframe,
                finalizado=False,
                preco_real=False,
                origem="tela",
            )
        )
    # O último elemento pode estar em formação; não presumir que está completo.
    return tuple(
        Candle(
            instante=vela.instante,
            abertura=vela.abertura,
            maxima=vela.maxima,
            minima=vela.minima,
            fechamento=vela.fechamento,
            timeframe=vela.timeframe,
            finalizado=indice < len(candles) - 1,
            preco_real=False,
            origem="tela",
        )
        for indice, vela in enumerate(candles)
    )


class ScreenSource(DataSource):
    """Capturador desacoplado, com ciclo próprio e estados explícitos."""

    def __init__(self, configuracao: Configuracao):
        if configuracao.regiao_grafico is None or configuracao.regiao_cabecalho is None:
            raise ValueError("É necessário calibrar gráfico e cabeçalho.")
        self.configuracao = configuracao
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self, ao_receber: AoReceber) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(
            target=self._executar, args=(ao_receber,), daemon=True, name="leitura-tela"
        )
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread and threading.current_thread() is not self._thread:
            self._thread.join(timeout=5)

    def _executar(self, ao_receber: AoReceber) -> None:
        from mss import mss

        config = self.configuracao
        assert config.regiao_grafico is not None
        assert config.regiao_cabecalho is not None
        identificacao: tuple[str | None, str | None, bool] = (None, None, False)
        ultimo_ocr = float("-inf")
        janela_fps = time.monotonic()
        quadros = 0
        fps = 0.0
        with mss() as captura:
            while not self._parar.is_set():
                inicio = time.monotonic()
                agora = datetime.now(timezone.utc)
                try:
                    if inicio - ultimo_ocr >= config.ocr_intervalo_segundos:
                        bruto = captura.grab(vars(config.regiao_cabecalho))
                        imagem_cabecalho = np.asarray(bruto)[:, :, :3].copy()
                        # Falhas de OCR invalidam a identificação, sem usar rótulos antigos.
                        ultimo_ocr = inicio
                        identificacao = identificar_cabecalho(extrair_texto(imagem_cabecalho))
                    ativo, timeframe, otc = identificacao
                    if otc:
                        amostra = Amostra(
                            ativo=ativo, timeframe=timeframe, estado=EstadoFonte.OTC_IGNORADO,
                            mensagem="OTC ignorado", fps=fps, instante_coleta=agora
                        )
                    elif not ativo or timeframe not in config.timeframes_permitidos:
                        amostra = Amostra(
                            ativo=ativo, timeframe=timeframe, estado=EstadoFonte.SEM_GRAFICO,
                            mensagem="Ativo/timeframe não confirmado por OCR; sem sinais",
                            fps=fps, instante_coleta=agora
                        )
                    else:
                        bruto = captura.grab(vars(config.regiao_grafico))
                        imagem_grafico = np.asarray(bruto)[:, :, :3].copy()
                        velas = extrair_velas(imagem_grafico, timeframe)
                        estado = (
                            EstadoFonte.ANALISANDO if len(velas) >= config.minimo_candles
                            else EstadoFonte.AGUARDAR if velas
                            else EstadoFonte.SEM_GRAFICO
                        )
                        amostra = Amostra(
                            ativo=ativo, timeframe=timeframe, candles=velas,
                            estado=estado, fps=fps, preco_real=False,
                            identificacao_confiavel=True, instante_coleta=agora,
                            mensagem=(
                                f"{len(velas)} candles relativos; sem preços/tempos históricos "
                                "confiáveis. Sinais desabilitados na etapa 2."
                            )
                        )
                except Exception as erro:
                    # Não incluir pixels, credenciais ou textos de OCR no log.
                    LOG.warning("Captura/OCR indisponível: %s", type(erro).__name__)
                    identificacao = (None, None, False)
                    amostra = Amostra(
                        ativo=None, timeframe=None, estado=EstadoFonte.ERRO,
                        mensagem="Falha de captura ou OCR; verificar Tesseract e calibração",
                        instante_coleta=agora
                    )
                try:
                    ao_receber(amostra)
                except Exception:
                    LOG.exception("Erro no consumidor dos dados da tela.")
                quadros += 1
                if time.monotonic() - janela_fps >= 1.0:
                    fps = quadros / (time.monotonic() - janela_fps)
                    quadros = 0
                    janela_fps = time.monotonic()
                self._parar.wait(max(0.0, 1.0 / config.captura_fps - (time.monotonic() - inicio)))
