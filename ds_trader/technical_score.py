"""Placar descritivo de critérios VISUAIS, nunca probabilidade de sucesso."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class TechnicalScore:
    alta: int
    baixa: int
    factors: int


def score_visual(result) -> TechnicalScore | None:
    """Exige identidade estável, imagem atual e pelo menos 2 grupos de critérios.

    Os pesos são escolhas heurísticas e correlacionadas. Jamais representam
    chance de vencer uma operação, nem feed de preços IQ Option.
    """
    if (result is None or not result.valid_roi or result.stale_frame or
            (result.identity_required and not result.identity_confirmed) or
            result.next_visual_bias not in ("ALTA", "BAIXA")):
        return None
    up = down = groups = 0
    if result.trend_visual == "ALTA":
        up += 2
        groups += 1
    elif result.trend_visual == "BAIXA":
        down += 2
        groups += 1
    if result.lta is not None or result.ltb is not None:
        groups += 1
        up += int(result.lta is not None)
        down += int(result.ltb is not None)
    found_up = any("de alta" in p.lower() for p in result.patterns)
    found_down = any("de baixa" in p.lower() for p in result.patterns)
    if found_up or found_down:
        groups += 1
        up += int(found_up)
        down += int(found_down)
    up_momentum = any("impulso recente de alta" in r.lower()
                      for r in result.visual_reasons)
    down_momentum = any("impulso recente de baixa" in r.lower()
                        for r in result.visual_reasons)
    if up_momentum or down_momentum:
        groups += 1
        up += int(up_momentum)
        down += int(down_momentum)
    votes = up + down
    if votes < 3 or groups < 2:
        return None
    pct = round(100 * up / votes)
    return TechnicalScore(pct, 100-pct, groups)
