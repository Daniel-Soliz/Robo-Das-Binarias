"""Pivôs e zonas de suporte/resistência por reação repetida."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from data_sources.base import Candle
from analysis.indicators import amplitude_tipica


@dataclass(frozen=True)
class Pivo:
    indice: int
    preco: float
    tipo: str


@dataclass(frozen=True)
class Zona:
    tipo: str
    inferior: float
    superior: float
    toques: int
    indices: tuple[int, ...]

    @property
    def centro(self) -> float:
        return (self.inferior + self.superior) / 2


def detectar_pivos(
    candles: Sequence[Candle], esquerda: int = 2, direita: int = 2
) -> tuple[Pivo, ...]:
    """Identifica extremos confirmados sem utilizar candles futuros não fechados."""
    if esquerda < 1 or direita < 1:
        raise ValueError("Janelas de pivô devem ser positivas.")
    serie = [c for c in candles if c.finalizado]
    pivos: list[Pivo] = []
    for i in range(esquerda, len(serie) - direita):
        janela = serie[i - esquerda: i + direita + 1]
        c = serie[i]
        if all(c.minima < outro.minima for j, outro in enumerate(janela) if j != esquerda):
            pivos.append(Pivo(i, c.minima, "suporte"))
        if all(c.maxima > outro.maxima for j, outro in enumerate(janela) if j != esquerda):
            pivos.append(Pivo(i, c.maxima, "resistencia"))
    return tuple(sorted(pivos, key=lambda item: (item.indice, item.tipo)))


def detectar_zonas(
    candles: Sequence[Candle],
    minimo_toques: int = 2,
    tolerancia: float | None = None,
) -> tuple[Zona, ...]:
    """Agrupa pivôs próximos por faixa de volatilidade; exige reações distintas."""
    serie = [c for c in candles if c.finalizado]
    if len(serie) < 7:
        return ()
    if minimo_toques < 2:
        raise ValueError("É obrigatório exigir pelo menos duas reações.")
    faixa = max(amplitude_tipica(serie) * 0.55, 1e-9) if tolerancia is None else tolerancia
    if faixa <= 0:
        raise ValueError("Tolerância deve ser positiva.")
    pivos = detectar_pivos(serie)
    zonas: list[Zona] = []
    for tipo in ("suporte", "resistencia"):
        grupos: list[list[Pivo]] = []
        for pivo in sorted((p for p in pivos if p.tipo == tipo), key=lambda p: p.preco):
            encontrou = False
            for grupo in grupos:
                centro = sum(p.preco for p in grupo) / len(grupo)
                if abs(pivo.preco - centro) <= faixa:
                    grupo.append(pivo)
                    encontrou = True
                    break
            if not encontrou:
                grupos.append([pivo])
        for grupo in grupos:
            indices = tuple(sorted({p.indice for p in grupo}))
            # Pivôs consecutivos são uma única região/reação.
            independentes = []
            for indice in indices:
                if not independentes or indice - independentes[-1] >= 3:
                    independentes.append(indice)
            if len(independentes) < minimo_toques:
                continue
            centro = sum(p.preco for p in grupo) / len(grupo)
            zonas.append(
                Zona(
                    tipo=tipo, inferior=centro - faixa, superior=centro + faixa,
                    toques=len(independentes), indices=tuple(independentes)
                )
            )
    return tuple(sorted(zonas, key=lambda z: (z.tipo, z.centro)))


def perto_de_zona(preco: float, zona: Zona, margem: float = 0.0) -> bool:
    """Testa presença dentro ou muito próximo de uma faixa."""
    return zona.inferior - margem <= preco <= zona.superior + margem

