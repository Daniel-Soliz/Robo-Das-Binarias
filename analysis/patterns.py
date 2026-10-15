"""Padrões de candlestick em candles encerrados, sem antecipar o futuro.

Os critérios são heurísticas estruturais. A direção da tendência e as zonas de
preço são confirmadas posteriormente no motor de análise, não aqui.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

from data_sources.base import Candle


@dataclass(frozen=True)
class Padrao:
    """Padrão detectado ao final de uma série fechada."""
    nome: str
    direcao: str
    quantidade_velas: int


def detectar_padroes(candles: Sequence[Candle]) -> tuple[Padrao, ...]:
    """Reconhece engolfos, harami, doji, pavios e padrões de 3 candles."""
    velas = [c for c in candles if c.finalizado]
    if not velas:
        return ()
    c = velas[-1]
    resultados: list[Padrao] = []

    def adicionar(nome: str, direcao: str, n: int) -> None:
        if (nome, direcao) not in {(p.nome, p.direcao) for p in resultados}:
            resultados.append(Padrao(nome, direcao, n))

    def corpo(v: Candle) -> float:
        return abs(v.fechamento - v.abertura)

    def amplitude(v: Candle) -> float:
        return max(v.maxima - v.minima, 1e-12)

    def sombra_sup(v: Candle) -> float:
        return v.maxima - max(v.abertura, v.fechamento)

    def sombra_inf(v: Candle) -> float:
        return min(v.abertura, v.fechamento) - v.minima

    def alta(v: Candle) -> bool:
        return v.fechamento > v.abertura

    def baixa(v: Candle) -> bool:
        return v.fechamento < v.abertura

    b = corpo(c)
    faixa = amplitude(c)
    sup, inf = sombra_sup(c), sombra_inf(c)
    if b <= faixa * 0.10:
        adicionar("doji", "NEUTRO", 1)
    if b >= faixa * 0.10:
        if inf >= max(b * 2, faixa * 0.5) and sup <= faixa * 0.2:
            adicionar("martelo", "COMPRA", 1)
            adicionar("pin bar de alta", "COMPRA", 1)
            # Enforcado: forma de martelo após tendência de alta.
            if len(velas) >= 4 and velas[-4].fechamento < velas[-2].fechamento:
                adicionar("enforcado", "VENDA", 1)
        if sup >= max(b * 2, faixa * 0.5) and inf <= faixa * 0.2:
            adicionar("martelo invertido", "COMPRA", 1)
            adicionar("estrela cadente", "VENDA", 1)
            adicionar("pin bar de baixa", "VENDA", 1)
    if len(velas) >= 2:
        a = velas[-2]
        # Engolfo: corpo de c contém o corpo de a, com cores opostas.
        if baixa(a) and alta(c) and c.abertura <= a.fechamento and c.fechamento >= a.abertura:
            if corpo(c) >= corpo(a) * 1.01:
                adicionar("engolfo de alta", "COMPRA", 2)
        if alta(a) and baixa(c) and c.abertura >= a.fechamento and c.fechamento <= a.abertura:
            if corpo(c) >= corpo(a) * 1.01:
                adicionar("engolfo de baixa", "VENDA", 2)
        # Harami: corpo da segunda vela contido no da primeira.
        if baixa(a) and alta(c) and c.abertura >= a.fechamento and c.fechamento <= a.abertura:
            if corpo(c) <= corpo(a) * 0.65:
                adicionar("harami de alta", "COMPRA", 2)
        if alta(a) and baixa(c) and c.abertura <= a.fechamento and c.fechamento >= a.abertura:
            if corpo(c) <= corpo(a) * 0.65:
                adicionar("harami de baixa", "VENDA", 2)
    if len(velas) >= 3:
        a, bvela = velas[-3], velas[-2]
        medio_a = (a.abertura + a.fechamento) / 2
        if baixa(a) and corpo(a) >= amplitude(a) * 0.45 and (
            corpo(bvela) <= amplitude(bvela) * 0.25
        ) and alta(c) and c.fechamento > medio_a:
            adicionar("estrela da manhã", "COMPRA", 3)
        if alta(a) and corpo(a) >= amplitude(a) * 0.45 and (
            corpo(bvela) <= amplitude(bvela) * 0.25
        ) and baixa(c) and c.fechamento < medio_a:
            adicionar("estrela da noite", "VENDA", 3)
        tres = velas[-3:]
        if all(alta(v) and corpo(v) >= amplitude(v) * 0.5 for v in tres):
            if all(tres[i].fechamento > tres[i - 1].fechamento for i in (1, 2)):
                adicionar("três soldados brancos", "COMPRA", 3)
        if all(baixa(v) and corpo(v) >= amplitude(v) * 0.5 for v in tres):
            if all(tres[i].fechamento < tres[i - 1].fechamento for i in (1, 2)):
                adicionar("três corvos negros", "VENDA", 3)
    return tuple(resultados)
