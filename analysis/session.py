"""Agrupador de M5/M15 para diagnóstico, sem publicar sinais operacionais."""

from __future__ import annotations

from datetime import datetime

from analysis.cooldown import CooldownCandidatos
from data_sources.base import Amostra, EstadoFonte
from analysis.signal_engine import Analise, MotorAnalise


class SessaoAnalise:
    """Não combina ativos diferentes, OTC ou fontes sem preço verificável."""

    def __init__(self, pontuacao_minima: int = 75, cooldown_segundos: int = 180):
        self.motor = MotorAnalise(pontuacao_minima)
        self.cooldown = CooldownCandidatos(cooldown_segundos)
        self._ativo: str | None = None
        self._origem: str | None = None
        self._series: dict[str, tuple] = {}

    def receber(self, amostra: Amostra) -> Analise:
        """Acumula séries separadas; qualquer problema reinicia o contexto."""
        if amostra.estado in (EstadoFonte.ERRO, EstadoFonte.OTC_IGNORADO,
                             EstadoFonte.SEM_GRAFICO):
            self._series.clear()
            self._ativo = None
            self._origem = None
            return Analise(estado=amostra.estado.value, motivos=(amostra.mensagem,))
        if (amostra.estado is not EstadoFonte.ANALISANDO
                or not amostra.identificacao_confiavel or not amostra.ativo
                or amostra.timeframe not in ("M5", "M15")
                or not amostra.preco_real or not amostra.candles):
            self._series.clear()
            return Analise(estado="AGUARDAR", motivos=("Captura sem OHLC real verificável.",))
        origem = amostra.candles[0].origem
        if self._ativo != amostra.ativo or self._origem != origem:
            self._series.clear()
        self._ativo, self._origem = amostra.ativo, origem
        self._series[amostra.timeframe] = amostra.candles
        if "M5" not in self._series or "M15" not in self._series:
            return Analise(estado="AGUARDAR", motivos=("Aguardando M5 e M15 completos.",))
        resultado = self.motor.analisar(
            amostra.ativo, self._series["M5"], self._series["M15"],
            agora=amostra.instante_coleta
        )
        if resultado.direcao_teorica and not self.cooldown.permitir(
            amostra.ativo, resultado.direcao_teorica, amostra.instante_coleta
        ):
            return Analise(
                estado="AGUARDAR", pontuacao=resultado.pontuacao,
                motivos=("Cooldown de candidato teórico ativo.",),
            )
        return resultado

