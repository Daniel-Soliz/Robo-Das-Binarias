"""Limitador de candidatos TEÓRICOS por ativo e direção, sem alertas operacionais."""

from __future__ import annotations

from datetime import datetime


class CooldownCandidatos:
    """Não repete uma hipótese no período configurado; recua com segurança."""

    def __init__(self, segundos: int = 180):
        if not 60 <= segundos <= 3600:
            raise ValueError("Cooldown deve ficar entre 60 e 3600 segundos.")
        self.segundos = segundos
        self._ultimo: dict[tuple[str, str], datetime] = {}

    def permitir(self, ativo: str, direcao: str, instante: datetime) -> bool:
        """Retorna False para duplicatas e relógio regressivo."""
        if instante.tzinfo is None:
            raise ValueError("Cooldown exige data com fuso horário.")
        chave = (ativo, direcao)
        anterior = self._ultimo.get(chave)
        if anterior is not None:
            intervalo = (instante - anterior).total_seconds()
            if intervalo < self.segundos:
                return False
        self._ultimo[chave] = instante
        return True
