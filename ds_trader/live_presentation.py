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
    side = result.bias if result.bias in ("CALL", "PUT") else "AGUARDAR"
    subtitle = "HIPÓTESE VISUAL EXPERIMENTAL" if side != "AGUARDAR" else "SEM CONFLUÊNCIA CONFIÁVEL"
    return LivePanelState(
        side, "up" if side == "CALL" else "down" if side == "PUT" else "warning",
        subtitle, result.movement,
        ", ".join(result.patterns) if result.patterns else "Nenhum padrão confirmado",
        ", ".join(result.structures) if result.structures else "Sem estruturas confirmadas",
        result.explanation, detected
    )
