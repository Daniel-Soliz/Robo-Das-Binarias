"""Compara cenarios VISUAIS, sem alegar probabilidades ou entradas negociaveis.

Pixels representam alturas relativas. Nao provam fechamento, expiracao, fonte
de cotacao, nem constituem amostra estatistica para estimar taxa de acerto.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class VisualOutlook:
    direction: str  # ALTA, BAIXA ou INDEFINIDO
    reasons: tuple[str, ...]
    recent_top: float | None = None
    recent_bottom: float | None = None


def compare_visual_scenarios(candles, opinion) -> VisualOutlook:
    """Aponta confluencias e vetos sem converter placar heuristico em porcentagem.

    Recebe somente as figuras anteriores estimadas. A ultima figura, que pode
    estar aberta, deve ser excluida pelo chamador.
    """
    if len(candles) < 25:
        return VisualOutlook("INDEFINIDO", ("Poucas velas reconhecidas.",))
    ranges = [c.high - c.low for c in candles[-14:]]
    avg_range = mean(ranges)
    if avg_range <= 0:
        return VisualOutlook("INDEFINIDO", ("Amplitude visual insuficiente.",))

    last = candles[-1]
    # Extremos nao sao suportes/resistencias comprovados, por isso sao
    # expostos separadamente dos pivos confirmados pelo motor tecnico.
    recent = candles[-18:]
    recent_top = max(c.high for c in recent)
    recent_bottom = min(c.low for c in recent)
    past_top = max(c.high for c in candles[-10:-1])
    past_bottom = min(c.low for c in candles[-10:-1])
    # Nao bloquear automaticamente um rompimento que ja ultrapassou o extremo.
    near_top = avg_range * .05 < past_top - last.close <= avg_range * 1.15
    near_bottom = avg_range * .05 < last.close - past_bottom <= avg_range * 1.15

    up = down = 0
    reasons: list[str] = []
    if opinion.trend == "ALTA":
        up += 2
        reasons.append("Tendência visual de alta nas médias de 9/21 velas")
    elif opinion.trend == "BAIXA":
        down += 2
        reasons.append("Tendência visual de baixa nas médias de 9/21 velas")
    if opinion.lta:
        up += 1
        reasons.append("Fundos ascendentes formam uma LTA")
    if opinion.ltb:
        down += 1
        reasons.append("Topos descendentes formam uma LTB")

    movement = last.close - candles[-4].close
    if movement > avg_range * .5:
        up += 1
        reasons.append("Impulso recente de alta")
    elif movement < -avg_range * .5:
        down += 1
        reasons.append("Impulso recente de baixa")

    latest = candles[-3:]
    bullish = sum(c.close > c.open for c in latest)
    bearish = sum(c.close < c.open for c in latest)
    if bullish >= 2:
        up += 1
    elif bearish >= 2:
        down += 1

    if near_top:
        reasons.append("Preço perto de topo recente: possível rejeição")
    if near_bottom:
        reasons.append("Preço perto de fundo recente: possível reação")

    # A proximidade de uma barreira oposta pode neutralizar o viés, mas não
    # equivale por si só a prever reversão. Sem confirmação: indefinido.
    if up >= down + 2 and not near_top:
        direction = "ALTA"
    elif down >= up + 2 and not near_bottom:
        direction = "BAIXA"
    else:
        direction = "INDEFINIDO"
        reasons.append("Sem vantagem visual clara para a próxima vela")
    if not reasons:
        reasons.append("Nenhuma confluência direcional reconhecida")
    return VisualOutlook(direction, tuple(reasons), recent_top, recent_bottom)
