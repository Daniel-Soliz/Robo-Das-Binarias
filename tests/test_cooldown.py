"""Testes determinísticos do cooldown de hipóteses não operacionais."""

from datetime import datetime, timedelta, timezone
from analysis.cooldown import CooldownCandidatos


def test_cooldown_por_ativo_e_direcao():
    atual = datetime(2026, 10, 15, 13, tzinfo=timezone.utc)
    limitador = CooldownCandidatos(segundos=180)
    assert limitador.permitir("EURUSD", "COMPRA", atual)
    assert not limitador.permitir("EURUSD", "COMPRA", atual + timedelta(seconds=179))
    assert limitador.permitir("EURUSD", "VENDA", atual + timedelta(seconds=3))
    assert limitador.permitir("GBPUSD", "COMPRA", atual + timedelta(seconds=3))
    assert limitador.permitir("EURUSD", "COMPRA", atual + timedelta(seconds=180))
    assert not limitador.permitir("EURUSD", "COMPRA", atual - timedelta(seconds=2))


def test_sem_operacao_ou_novo_alerta_no_cooldown():
    atual = datetime(2026, 10, 15, 13, tzinfo=timezone.utc)
    limitador = CooldownCandidatos()
    assert limitador.permitir("EURUSD", "COMPRA", atual)
    assert not limitador.permitir("EURUSD", "COMPRA", atual)
