"""Cálculos conhecidos e casos extremos dos indicadores."""

import pytest

from analysis.indicators import ema, rsi


def test_ema_constante_e_aquecimento():
    valores = [10.0] * 70
    serie = ema(valores, 9)
    assert all(v is None for v in serie[:8])
    assert all(v == pytest.approx(10.0) for v in serie[8:])


def test_ema_resposta_a_subida():
    valores = [10.0] * 30 + [20.0] * 30
    serie = ema(valores, 9)
    assert serie[-1] > serie[30]
    assert 19.9 < serie[-1] < 20


def test_rsi_basico():
    assert rsi([8.0] * 30)[-1] == 50
    assert rsi([float(i) for i in range(30)])[-1] == 100
    assert rsi([float(30 - i) for i in range(30)])[-1] == 0
    assert all(item is None for item in rsi([1, 2, 3], 14))


def test_periodo_invalido():
    with pytest.raises(ValueError):
        ema([1, 2, 3], 1)
    with pytest.raises(ValueError):
        rsi([1, float("nan")], 14)
