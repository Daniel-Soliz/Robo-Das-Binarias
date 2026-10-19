"""Confluência M15/M5 conservadora, SEM habilitação de alertas operacionais.

Esta etapa calcula SOMENTE hipóteses para estudos. Não emite ordem, clique,
notificação de entrada ou sinal executável; operacional permanece False.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median

from data_sources.base import Candle
from analysis.indicators import amplitude_tipica, ema, rsi, tendencia_emas
from analysis.levels import detectar_zonas, perto_de_zona
from analysis.patterns import detectar_padroes
from analysis.trendlines import detectar_linhas
from utils.ocr import eh_otc


@dataclass(frozen=True)
class Analise:
    """Resultado diagnóstico; score NÃO equivale a probabilidade de acerto."""

    estado: str
    pontuacao: int = 0
    direcao_teorica: str | None = None
    motivos: tuple[str, ...] = ()
    operacional: bool = False
    validade_segundos: int = 0


@dataclass(frozen=True)
class Criterios:
    """Critérios binários de pontuação; 100 pontos no máximo."""

    tendencia_m15: bool = False
    zona: bool = False
    padrao: bool = False
    linha: bool = False
    medias_m5: bool = False
    rsi_m5: bool = False


def pontuar(criterios: Criterios) -> tuple[int, tuple[str, ...]]:
    """Soma pesos explícitos sem contar múltiplos padrões duas vezes."""
    itens = (
        (criterios.tendencia_m15, 25, "Tendência confirmada no M15"),
        (criterios.zona, 20, "Reação em zona de suporte/resistência"),
        (criterios.padrao, 20, "Padrão de candle direcional"),
        (criterios.linha, 15, "Toque ou reteste na linha de tendência"),
        (criterios.medias_m5, 10, "EMAs 9/21/50 alinhadas no M5"),
        (criterios.rsi_m5, 10, "RSI(14) coerente com a direção"),
    )
    return (
        sum(pontos for aprovado, pontos, _ in itens if aprovado),
        tuple(motivo for aprovado, _, motivo in itens if aprovado),
    )


def _serie_validada(
    candles: Sequence[Candle], timeframe: str, agora: datetime,
) -> tuple[Candle, ...] | None:
    """Rejeita OHLC relativo, lacunas, candles abertos e históricos defasados."""
    if len(candles) < 60:
        return None
    if any(
        c.timeframe != timeframe or not c.preco_real or c.instante is None
        for c in candles
    ):
        return None
    # Apenas fechado, sem corrigir barras abertas como se fossem fechadas.
    serie = tuple(c for c in candles if c.finalizado)
    if len(serie) < 60:
        return None
    ultimos = serie[-60:]
    segundos = {"M5": 300, "M15": 900}[timeframe]
    instantes = [c.instante for c in ultimos]
    if any(x is None or x.tzinfo is None for x in instantes):
        return None
    epocas = [x.timestamp() for x in instantes if x is not None]
    if any(
        abs((b - a) - segundos) > 2 for a, b in zip(epocas, epocas[1:])
    ):
        return None
    idade = agora.timestamp() - epocas[-1]
    if idade < segundos or idade > segundos * 2 + 90:
        return None
    return ultimos


class MotorAnalise:
    """Executa análise de contexto M15 + gatilho M5 sem liberar operações."""

    def __init__(self, pontuacao_minima: int = 75):
        if not 50 <= pontuacao_minima <= 100:
            raise ValueError("Pontuação mínima deve estar entre 50 e 100.")
        self.pontuacao_minima = pontuacao_minima

    def analisar(
        self,
        ativo: str,
        candles_m5: Sequence[Candle],
        candles_m15: Sequence[Candle],
        agora: datetime | None = None,
    ) -> Analise:
        """Avalia SOMENTE séries independentes já completas e auditáveis."""
        if not ativo or eh_otc(ativo):
            return Analise(estado="OTC ignorado" if eh_otc(ativo) else "AGUARDAR",
                           motivos=("Ativo ausente ou OTC.",))
        instante = agora or datetime.now(timezone.utc)
        if instante.tzinfo is None:
            raise ValueError("O relógio deve ter timezone.")
        m5 = _serie_validada(candles_m5, "M5", instante)
        m15 = _serie_validada(candles_m15, "M15", instante)
        if not m5 or not m15:
            return Analise(
                estado="AGUARDAR",
                motivos=("Dados M5/M15 insuficientes, atrasados ou não verificáveis.",)
            )
        direcao_m15 = tendencia_emas(m15)
        if direcao_m15 == "lateral":
            return Analise(
                estado="AGUARDAR",
                motivos=("M15 sem tendência confirmada ou em lateralização.",)
            )
        direcao = "COMPRA" if direcao_m15 == "alta" else "VENDA"
        ultimo = m5[-1]
        fechamento = [c.fechamento for c in m5]
        amplitude = amplitude_tipica(m5)
        if amplitude <= 0:
            return Analise(estado="AGUARDAR", motivos=("Sem volatilidade mensurável.",))
        e9, e21, e50 = (ema(fechamento, p)[-1] for p in (9, 21, 50))
        indice_rsi = rsi(fechamento, 14)[-1]
        if e9 is None or e21 is None or e50 is None or indice_rsi is None:
            return Analise(estado="AGUARDAR", motivos=("Indicadores não aquecidos.",))
        # Não pontuar mercados com EMAs muito próximas (lateralidade).
        if abs(e21 - e50) < amplitude * .18:
            return Analise(estado="AGUARDAR", motivos=("M5 lateral; evitar entrada.",))
        corpos_previos = [abs(c.fechamento - c.abertura) for c in m5[-21:-1]]
        referencia = max(median(corpos_previos), amplitude * .2)
        if abs(ultimo.fechamento - ultimo.abertura) > referencia * 2.8:
            return Analise(estado="AGUARDAR", motivos=("Última vela esticada.",))
        if not 20 <= indice_rsi <= 80:
            return Analise(estado="AGUARDAR", motivos=("RSI extremo; evitar entrada.",))

        medias = e9 > e21 > e50 if direcao == "COMPRA" else e9 < e21 < e50
        rsi_ok = (45 <= indice_rsi <= 72) if direcao == "COMPRA" else (28 <= indice_rsi <= 55)
        zonas = detectar_zonas(m5)
        zonas_compativeis = [
            z for z in zonas if z.tipo == ("suporte" if direcao == "COMPRA" else "resistencia")
        ]
        extremo = ultimo.minima if direcao == "COMPRA" else ultimo.maxima
        em_zona = any(perto_de_zona(extremo, z, margem=amplitude * .25) for z in zonas_compativeis)
        padroes = [
            p for p in detectar_padroes(m5) if p.direcao == direcao
        ]
        linhas = detectar_linhas(m5)
        linha_ok = any(
            linha.tipo == ("LTA" if direcao == "COMPRA" else "LTB")
            and linha.evento == "toque"
            and linha.toques >= 2
            for linha in linhas
        )
        criterios = Criterios(
            tendencia_m15=True, zona=em_zona, padrao=bool(padroes),
            linha=linha_ok, medias_m5=medias, rsi_m5=rsi_ok,
        )
        pontos, motivos = pontuar(criterios)
        if padroes:
            motivos += ("Padrão: " + ", ".join(p.nome for p in padroes[:2]),)
        # Exigir gatilho estrutural E de candle; somente EMAs não bastam.
        if not padroes or not (em_zona or linha_ok) or pontos < self.pontuacao_minima:
            return Analise(
                estado="AGUARDAR",
                pontuacao=pontos,
                motivos=motivos + ("Confluência insuficiente para estudo.",),
            )
        # Bloqueio INCONDICIONAL da Etapa 3; deliberadamente sem configuração de desbloqueio.
        return Analise(
            estado="CANDIDATO TEÓRICO — NÃO OPERACIONAL",
            pontuacao=pontos,
            direcao_teorica=direcao,
            motivos=motivos + ("Sinal bloqueado até validação real da leitura.",),
            operacional=False,
            validade_segundos=0,
        )

