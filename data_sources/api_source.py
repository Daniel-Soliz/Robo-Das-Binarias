"""Fonte alternativa experimental: lê candles de API comunitária não oficial.

AVISO: get_candles pode devolver dados com atraso, inadequados para uma
decisão de expiração de 60 segundos. Nenhuma função de operação é utilizada.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from dotenv import load_dotenv

from config import Configuracao
from data_sources.base import Amostra, AoReceber, Candle, DataSource, EstadoFonte
from utils.ocr import eh_otc

LOG = logging.getLogger(__name__)


def converter_candles_api(
    dados: list[dict[str, Any]], timeframe: str, agora: float | None = None
) -> tuple[Candle, ...]:
    """Normaliza OHLC da API; remove duplicatas e rejeita valores inválidos."""
    periodo = {"M5": 300, "M15": 900}[timeframe]
    atual = time.time() if agora is None else agora
    por_instante: dict[int, Candle] = {}
    for item in dados:
        try:
            inicio = int(item["from"])
            if inicio <= 0 or inicio > atual + periodo:
                continue
            candle = Candle(
                instante=datetime.fromtimestamp(inicio, tz=timezone.utc),
                abertura=float(item["open"]),
                maxima=float(item["max"]),
                minima=float(item["min"]),
                fechamento=float(item["close"]),
                timeframe=timeframe,
                # Tratar como fechado somente se tempo da barra terminou.
                finalizado=(inicio + periodo <= atual),
                preco_real=True,
                origem="api",
            )
            por_instante[inicio] = candle
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
    return tuple(por_instante[instante] for instante in sorted(por_instante))


class ApiSource(DataSource):
    """Adaptador de leitura. Aceita fábrica injetável para testes simulados."""

    def __init__(
        self,
        configuracao: Configuracao,
        fabrica_cliente: Callable[[str, str], Any] | None = None,
    ):
        self.configuracao = configuracao
        self._fabrica_cliente = fabrica_cliente
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def iniciar(self, ao_receber: AoReceber) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._parar.clear()
        self._thread = threading.Thread(
            target=self._executar, args=(ao_receber,), daemon=True, name="leitura-api"
        )
        self._thread.start()

    def parar(self) -> None:
        self._parar.set()
        if self._thread and threading.current_thread() is not self._thread:
            self._thread.join(timeout=5)

    def _notificar(
        self, receptor: AoReceber, estado: EstadoFonte, mensagem: str,
        ativo: str | None = None, periodo: str | None = None,
        candles: tuple[Candle, ...] = (),
    ) -> None:
        amostra = Amostra(
            ativo=ativo,
            timeframe=periodo,
            candles=candles,
            estado=estado,
            mensagem=mensagem,
            preco_real=bool(candles),
            identificacao_confiavel=bool(ativo),
        )
        try:
            receptor(amostra)
        except Exception:
            LOG.exception("Erro ao entregar amostra da API.")

    def _executar(self, ao_receber: AoReceber) -> None:
        load_dotenv()
        ativo = self.configuracao.api_ativo.upper().strip()
        if eh_otc(ativo):
            self._notificar(ao_receber, EstadoFonte.OTC_IGNORADO, "OTC ignorado", ativo)
            return
        if not re.fullmatch(r"[A-Z]{6}", ativo):
            self._notificar(ao_receber, EstadoFonte.ERRO, "Par Forex inválido no config.json")
            return
        if os.getenv("IQ_CONTA_DEMO_CONFIRMADA", "").upper() != "SIM":
            self._notificar(
                ao_receber, EstadoFonte.ERRO,
                "Modo API bloqueado: confirme conta DEMO em .env"
            )
            return
        usuario, senha = os.getenv("IQ_EMAIL"), os.getenv("IQ_PASSWORD")
        if not usuario or not senha:
            self._notificar(ao_receber, EstadoFonte.ERRO, "Credenciais ausentes no .env")
            return
        try:
            if self._fabrica_cliente is None:
                from iqoptionapi.stable_api import IQ_Option

                fabrica = IQ_Option
            else:
                fabrica = self._fabrica_cliente
        except ImportError:
            self._notificar(
                ao_receber, EstadoFonte.ERRO,
                "Instale a dependência opcional iqoptionapi; consulte README"
            )
            return

        cliente = None
        espera_reconexao = 5.0
        while not self._parar.is_set():
            try:
                if cliente is None:
                    cliente = fabrica(usuario, senha)
                if not cliente.check_connect():
                    resposta = cliente.connect()
                    conectado = resposta[0] if isinstance(resposta, (tuple, list)) else bool(resposta)
                    if not conectado:
                        raise ConnectionError("Falha na conexão de leitura")
                # Consulta apenas candles. Não alterar o tipo de conta ou emitir operações.
                for periodo, segundos in (("M5", 300), ("M15", 900)):
                    if self._parar.is_set():
                        return
                    dados = cliente.get_candles(ativo, segundos, 100, time.time())
                    if not isinstance(dados, list):
                        raise ValueError("API não retornou uma lista de candles")
                    velas = converter_candles_api(dados, periodo)
                    idade = (
                        time.time() - velas[-1].instante.timestamp()
                        if velas and velas[-1].instante else float("inf")
                    )
                    if len(velas) < self.configuracao.minimo_candles:
                        estado = EstadoFonte.AGUARDAR
                        mensagem = "Histórico insuficiente; sem sinais."
                    elif idade > segundos + 60:
                        estado = EstadoFonte.AGUARDAR
                        mensagem = "Dados potencialmente atrasados; sem sinais."
                    else:
                        estado = EstadoFonte.ANALISANDO
                        mensagem = (
                            "Candles recebidos por API não oficial; dados podem atrasar "
                            "até ~30 s. Sinais desabilitados na etapa 2."
                        )
                    self._notificar(
                        ao_receber, estado, mensagem, ativo, periodo, velas
                    )
                espera_reconexao = 5.0
                self._parar.wait(self.configuracao.api_intervalo_segundos)
            except Exception as erro:
                LOG.warning("Conexão/leitura API falhou: %s", type(erro).__name__)
                cliente = None
                self._notificar(
                    ao_receber, EstadoFonte.ERRO,
                    "Conexão de leitura indisponível; nova tentativa automática",
                    ativo
                )
                self._parar.wait(espera_reconexao)
                espera_reconexao = min(espera_reconexao * 2, 60.0)

