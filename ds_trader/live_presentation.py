"""Formatação isolada da apresentação. Não altera a análise nem dispara ordens."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class LivePanelState:
    side: str
    tone: str
    subtitle: str
    status: str
    pattern: str
    structure: str
    detail: str
    detected_label: str
    outlook: str = "SEM VANTAGEM CLARA"
    outlook_reason: str = "Aguardando leitura visual."


def presentation_for(result, *, obscured: bool = False) -> LivePanelState:
    """Nunca apresenta CALL/PUT se a captura for ilegível ou encoberta pelo app.

    'Força de critérios' ou porcentagens de acerto NÃO são estimadas a partir
    de pixels; por isso só mostra o estado condicional e a explicação.
    """
    detected = f"{result.completed_estimate} velas anteriores estimadas"
    if obscured:
        return LivePanelState(
            "AGUARDAR", "warning", "GRÁFICO ENCOBERTO",
            "Mova o DS Trader para o lado ou use outro monitor.",
            "Não verificável", "Não verificável",
            "A janela do DS Trader está cobrindo parte da região selecionada. "
            "Para monitorar a IQ Option, mantenha o gráfico visível sem sobreposição. "
            "Nenhum sinal é permitido durante esta condição.", detected
        )
    if not result.valid_roi:
        return LivePanelState(
            "AGUARDAR", "warning", "LEITURA INSUFICIENTE",
            "Selecione apenas os candles, sem navegador, menus ou botões.",
            "Ainda não reconhecidos", "Ainda não identificadas",
            result.explanation, detected
        )
    if result.identity_required and not result.identity_confirmed:
        return LivePanelState(
            "AGUARDAR", "warning", "ATIVO NÃO CONFIRMADO",
            "Aguardando leitura consistente do nome do ativo e período.",
            "Ainda não verificáveis", "Ainda não verificáveis",
            result.identity_reason + " Nenhuma hipótese anterior é reaproveitada.",
            detected,
        )
    outlook = {
        "ALTA": "ALTA FAVORECIDA",
        "BAIXA": "BAIXA FAVORECIDA",
    }.get(result.next_visual_bias, "SEM VANTAGEM CLARA")
    focus = (result.visual_reasons[-2:] if result.next_visual_bias == "INDEFINIDO"
             else result.visual_reasons[:3])
    reasons = "; ".join(focus) or "Sem confluências visuais identificadas."
    if not result.temporal_verified:
        trend = (f"Viés visual: {result.trend_visual}. "
                 if result.trend_visual in ("ALTA", "BAIXA") else "")
        return LivePanelState(
            "AGUARDAR", "warning", "FECHAMENTO / RELOGIO NAO VERIFICADOS",
            trend + "Sem confirmação temporal para entrada.",
            ", ".join(result.patterns) if result.patterns else "Nenhum padrao comprovado",
            ("Tendência visual: " + result.trend_visual + ". "
             if result.trend_visual in ("ALTA", "BAIXA") else "") +
            (", ".join(result.structures) if result.structures else "Sem estruturas reconhecidas"),
            result.explanation, detected, outlook, reasons,
        )
    side = result.bias if result.bias in ("CALL", "PUT") else "AGUARDAR"
    subtitle = "HIPÓTESE VISUAL EXPERIMENTAL" if side != "AGUARDAR" else "SEM CONFLUÊNCIA CONFIÁVEL"
    return LivePanelState(
        side, "up" if side == "CALL" else "down" if side == "PUT" else "warning",
        subtitle, result.movement,
        ", ".join(result.patterns) if result.patterns else "Nenhum padrão confirmado",
        ", ".join(result.structures) if result.structures else "Sem estruturas confirmadas",
        result.explanation, detected, outlook, reasons,
    )


def screen_region_is_obscured(region, own_window, threshold=0.08):
    """True quando uma janela cobre parte significativa da região capturada.

    region: Region com left/top/width/height.
    own_window: (x, y, width, height) coordenadas físicas do DS Trader.
    """
    x, y, width, height = own_window
    if region.width <= 0 or region.height <= 0 or width <= 0 or height <= 0:
        return False
    overlap_width = max(0, min(region.left + region.width, x + width)
                           - max(region.left, x))
    overlap_height = max(0, min(region.top + region.height, y + height)
                            - max(region.top, y))
    return (overlap_width * overlap_height /
            (region.width * region.height)) > threshold
