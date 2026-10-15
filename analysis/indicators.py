"""Indicadores calculados apenas com candles fechados, sem dependência de TA-Lib."""

from __future__ import annotations

from collections.abc import Sequence
import math

from data_sources.base import Candle


def _validar(valores: Sequence[float], periodo: int) -> None:
    """Valida parâmetros e números finitos."""
    if periodo < 2:
        raise ValueError("Período deve ser >= 2.")
    if any(not math.isfinite(v) for v in valores):
        raise ValueError("Série contém números não finitos.")


def ema(valores: Sequence[float], periodo: int) -> list[float | None]:
    """EMA com média simples inicial; índices anteriores ficam indisponíveis."""
    _validar(valores, periodo)
    resultado: list[float | None] = [None] * len(valores)
    if len(valores) < periodo:
        return resultado
    anterior = sum(valores[:periodo]) / periodo
    resultado[periodo - 1] = anterior
    fator = 2 / (periodo + 1)
    for i in range(periodo, len(valores)):
        anterior = fator * valores[i] + (1 - fator) * anterior
        resultado[i] = anterior
    return resultado


def rsi(valores: Sequence[float], periodo: int = 14) -> list[float | None]:
    """RSI de Wilder, inicializado após 'periodo' variações."""
    _validar(valores, periodo)
    resultado: list[float | None] = [None] * len(valores)
    if len(valores) <= periodo:
        return resultado
    ganhos = [max(0.0, valores[i] - valores[i - 1]) for i in range(1, len(valores))]
    perdas = [max(0.0, valores[i - 1] - valores[i]) for i in range(1, len(valores))]
    ganho = sum(ganhos[:periodo]) / periodo
    perda = sum(perdas[:periodo]) / periodo

    def calcular(g: float, p: float) -> float:
        if g == 0 and p == 0:
            return 50.0
        if p == 0:
            return 100.0
        return 100 - 100 / (1 + g / p)

    resultado[periodo] = calcular(ganho, perda)
    for i in range(periodo + 1, len(valores)):
        ganho = (ganho * (periodo - 1) + ganhos[i - 1]) / periodo
        perda = (perda * (periodo - 1) + perdas[i - 1]) / periodo
        resultado[i] = calcular(ganho, perda)
    return resultado


def amplitude_tipica(candles: Sequence[Candle], quantidade: int = 20) -> float:
    """Mediana da amplitude de candles, resistente a outliers isolados."""
    import statistics
    if not candles:
        return 0.0
    return statistics.median(c.maxima - c.minima for c in candles[-quantidade:])


def tendencia_emas(candles: Sequence[Candle]) -> str:
    """Tendência pelas EMAs 9/21/50; retorna alta, baixa ou lateral."""
    if len(candles) < 55:
        return "lateral"
    fechamentos = [c.fechamento for c in candles]
    e9, e21, e50 = (ema(fechamentos, periodo)[-1] for periodo in (9, 21, 50))
    if e9 is None or e21 is None or e50 is None:
        return "lateral"
    amplitude = amplitude_tipica(candles)
    if amplitude <= 0 or abs(e21 - e50) < amplitude * 0.25:
        return "lateral"
    if e9 > e21 > e50 and fechamentos[-1] > e21:
        return "alta"
    if e9 < e21 < e50 and fechamentos[-1] < e21:
        return "baixa"
    return "lateral"
