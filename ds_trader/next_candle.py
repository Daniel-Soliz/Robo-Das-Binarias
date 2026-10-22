"""Motor explicavel de hipotese direcional para a proxima vela (nao envia ordens).

Regras conservadoras, sem IA, sem promessa de performance. Exige candles fechados.
Diferencia OHLC da API (preco real do fornecedor) de OHLC relativo aos pixels.
Padrões inspirados em definicoes publicas da TA-Lib, sem alegar equivalencia exata:
https://ta-lib.org/functions/cdlengulfing.html
https://ta-lib.org/functions/cdldoji.html
https://ta-lib.org/functions/cdlhammer
"""
from __future__ import annotations
from dataclasses import dataclass
from statistics import mean
from typing import Sequence


@dataclass(frozen=True)
class NextCandleOpinion:
    side: str  # CALL, PUT ou AGUARDAR
    trend: str
    patterns: tuple[str, ...]
    support: float | None
    resistance: float | None
    lta: tuple[float, float] | None  # projeções relativas a indice -2 e -1
    ltb: tuple[float, float] | None
    reasons: tuple[str, ...]
    caveat: str
    score_up: int = 0
    score_down: int = 0


def _pivots(data: Sequence, field: str) -> list[tuple[int, float]]:
    found = []
    for i in range(2, len(data) - 2):
        value = getattr(data[i], field)
        others = [getattr(data[j], field) for j in range(i-2, i+3) if j != i]
        if ((field == "low" and value < min(others)) or
                (field == "high" and value > max(others))):
            found.append((i, value))
    return found


def _line(pivots: list[tuple[int, float]], count: int, rising: bool):
    if len(pivots) < 2:
        return None
    a, b = pivots[-2:]
    if b[0] - a[0] < 3 or (b[1] > a[1]) != rising or b[1] == a[1]:
        return None
    slope = (b[1]-a[1])/(b[0]-a[0])
    # Evita extrapolacao excessiva de linhas antigas.
    if count-1-b[0] > 12:
        return None
    return (a[1]+slope*(count-2-a[0]), a[1]+slope*(count-1-a[0]))


def _patterns(candles):
    """Padrões observados no ultimo candle JA FECHADO. Nao concluem direcao."""
    current = candles[-1]
    prior = candles[-2]
    lo, hi = current.low, current.high
    spread = max(hi-lo, 1e-12)
    body = abs(current.close-current.open)
    lower = min(current.close,current.open)-lo
    upper = hi-max(current.close,current.open)
    tags = []
    if body <= .10*spread:
        tags.append("Doji / indecisao")
    if body >= .08*spread and body <= .36*spread and lower >= 2*body and upper <= .30*spread:
        tags.append("Martelo / rejeicao inferior")
    if body >= .08*spread and body <= .36*spread and upper >= 2*body and lower <= .30*spread:
        tags.append("Pavio superior longo")
    if (prior.close < prior.open and current.close > current.open and
            current.open <= prior.close and current.close >= prior.open):
        tags.append("Engolfo de alta")
    if (prior.close > prior.open and current.close < current.open and
            current.open >= prior.close and current.close <= prior.open):
        tags.append("Engolfo de baixa")
    if current.high < prior.high and current.low > prior.low:
        tags.append("Inside bar")
    return tuple(tags)


def evaluate_next(candles: Sequence, *, source: str, closed_confirmed: bool) -> NextCandleOpinion:
    """Analise de proxima barra somente por confluencia, com abstencao por padrao.

    closed_confirmed deve ser comprovado pela fonte; na tela sao apenas barras
    ESTIMADAS, logo o sinal e hipotese visual e nunca execucao autorizada.
    """
    caveat = (
        "Hipotese estatisticamente NAO validada. Nao e ordem, garantia nem "
        "indicacao de resultado em opcoes binarias. "
        + ("Pixels relativos; candle/horario reais nao comprovados."
           if source == "screen" else
           "Cotacoes do fornecedor podem diferir da corretora.")
    )
    def wait(reason, *, pats=(), support=None, resistance=None, lta=None, ltb=None,
             trend="INDEFINIDA", up=0, down=0):
        return NextCandleOpinion("AGUARDAR", trend, tuple(pats), support, resistance,
                                 lta, ltb, (reason,), caveat, up, down)
    # Mesmo sem prova temporal, podemos DESCREVER estruturas em pixels para a
    # previa. A hipotese direcional, porem, fica obrigatoriamente bloqueada.
    if len(candles) < 25:
        return wait(f"Somente {len(candles)} candles fechados; minimo 25 para avaliar contexto.")
    if any(not (c.low <= c.open <= c.high and c.low <= c.close <= c.high) for c in candles):
        return wait("OHLC inconsistente; sem hipotese.")
    last = candles[-1]
    closes = [c.close for c in candles]
    avg_range = mean(c.high-c.low for c in candles[-14:])
    if avg_range <= 1e-12:
        return wait("Candles sem amplitude suficiente para avaliar regioes.")
    tolerance = avg_range*.35
    sma9 = mean(closes[-9:]); sma21 = mean(closes[-21:])
    trend = ("ALTA" if sma9 > sma21+avg_range*.15 else
             "BAIXA" if sma9 < sma21-avg_range*.15 else "INDEFINIDA")
    highs = _pivots(candles, "high")
    lows = _pivots(candles, "low")
    support = max((v for _i,v in lows if v <= last.close), default=None)
    resistance = min((v for _i,v in highs if v >= last.close), default=None)
    lta = _line(lows, len(candles), rising=True)
    ltb = _line(highs, len(candles), rising=False)
    pats = _patterns(candles)
    reasons = [f"Tendencia de medias (9/21 candles): {trend}."]
    up = down = 0
    if trend == "ALTA":
        up += 1
    elif trend == "BAIXA":
        down += 1
    if lta:
        reasons.append("LTA: dois fundos ascendentes confirmados por pivôs.")
        if abs(last.close-lta[1]) < avg_range*1.3:
            up += 1
            reasons.append("Ultimo fechamento perto da LTA projetada.")
    if ltb:
        reasons.append("LTB: dois topos descendentes confirmados por pivôs.")
        if abs(last.close-ltb[1]) < avg_range*1.3:
            down += 1
            reasons.append("Ultimo fechamento perto da LTB projetada.")
    if support is not None:
        reasons.append("Suporte: nivel de fundo anterior confirmado.")
        if abs(last.close-support) < avg_range*1.2:
            up += 1
            reasons.append("Preco visual/provedor proximo ao suporte.")
    if resistance is not None:
        reasons.append("Resistencia: nivel de topo anterior confirmado.")
        if abs(resistance-last.close) < avg_range*1.2:
            down += 1
            reasons.append("Preco visual/provedor proximo a resistencia.")
    if not closed_confirmed:
        return wait("Fechamento do candle nao confirmado; estruturas somente visuais, "
                    "sem CALL/PUT acionavel.", pats=pats, support=support,
                    resistance=resistance, lta=lta, ltb=ltb, trend=trend,
                    up=up, down=down)
    if "Doji / indecisao" in pats or "Inside bar" in pats:
        return wait("Indecisao/contracao no ultimo candle: aguardar confirmacao.",
                    pats=pats, support=support, resistance=resistance, lta=lta,
                    ltb=ltb, trend=trend, up=up, down=down)
    for pat in pats:
        reasons.append("Padrao: " + pat + ".")
    if "Engolfo de alta" in pats:
        up += 2
    if "Engolfo de baixa" in pats:
        down += 2
    if "Martelo / rejeicao inferior" in pats and last.close > last.open:
        up += 1
    if "Pavio superior longo" in pats and last.close < last.open:
        down += 1
    # Resistencia a curta distancia desaconselha CALL; suporte idem para PUT.
    blocked_up = resistance is not None and resistance-last.close < tolerance
    blocked_down = support is not None and last.close-support < tolerance
    side = "AGUARDAR"
    if up >= 3 and up-down >= 2 and not blocked_up:
        side = "CALL"
    elif down >= 3 and down-up >= 2 and not blocked_down:
        side = "PUT"
    if side == "AGUARDAR":
        reasons.append("Sem confluencia suficiente ou regiao oposta proxima; aguardar.")
    else:
        reasons.append(
            f"HIPOTESE {side} para a proxima barra observada; "
            "nao entrar com base apenas nesta leitura.")
    return NextCandleOpinion(side, trend, pats, support, resistance, lta, ltb,
                             tuple(reasons), caveat, up, down)
