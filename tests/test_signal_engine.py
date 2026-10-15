"""Confluência segura e bloqueios de dados duvidosos."""

from datetime import datetime, timedelta, timezone

import pytest

from analysis.signal_engine import Criterios, MotorAnalise, pontuar
from analysis.session import SessaoAnalise
from data_sources.base import Amostra, Candle, EstadoFonte

AGORA = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)


def series(timeframe, n=70, tendencia=.0002, real=True, offset=0):
    periodo = 300 if timeframe == "M5" else 900
    inicio = AGORA - timedelta(seconds=periodo * (n + 1))
    saida = []
    for i in range(n):
        centro = (0.5 if not real else 1.1) + (i + offset) * tendencia
        saida.append(Candle(
            instante=inicio + timedelta(seconds=periodo * i) if real else None,
            abertura=centro-.0001, maxima=centro+.00025,
            minima=centro-.00025, fechamento=centro+.0001,
            timeframe=timeframe, finalizado=True, preco_real=real,
            origem="api" if real else "tela"
        ))
    return tuple(saida)


def test_pontuacao_e_criterios_independentes():
    assert pontuar(Criterios())[0] == 0
    assert pontuar(Criterios(True, True, True, True, True, True))[0] == 100
    assert pontuar(Criterios(tendencia_m15=True, padrao=True))[0] == 45


def test_motor_falha_fechado_para_otc_dados_relativos_e_lacunas():
    motor = MotorAnalise()
    m5, m15 = series("M5"), series("M15")
    assert motor.analisar("EURUSD-OTC", m5, m15, AGORA).estado == "OTC ignorado"
    relativo = series("M5", real=False)
    assert motor.analisar("EURUSD", relativo, m15, AGORA).estado == "AGUARDAR"
    com_lacuna = m15[:20] + m15[21:]
    assert motor.analisar("EURUSD", m5, com_lacuna, AGORA).estado == "AGUARDAR"
    atrasado = AGORA + timedelta(days=1)
    assert motor.analisar("EURUSD", m5, m15, atrasado).estado == "AGUARDAR"


def test_lateralizacao_nao_produz_sinal():
    motor = MotorAnalise(50)
    resultado = motor.analisar(
        "EURUSD", series("M5", tendencia=0), series("M15", tendencia=0), AGORA
    )
    assert resultado.estado == "AGUARDAR"
    assert resultado.direcao_teorica is None
    assert not resultado.operacional


def test_motor_nunca_habilita_alerta_operacional():
    motor = MotorAnalise(50)
    resultado = motor.analisar("EURUSD", series("M5"), series("M15"), AGORA)
    assert not resultado.operacional
    assert resultado.validade_segundos == 0
    with pytest.raises(ValueError):
        MotorAnalise(5)


def test_sessao_nao_mistura_ativos_e_rejeita_otc():
    sessao = SessaoAnalise()
    m5 = series("M5")
    m15 = series("M15")
    def amostra(ativo, timeframe, velas):
        return Amostra(
            ativo=ativo, timeframe=timeframe, candles=velas,
            estado=EstadoFonte.ANALISANDO, preco_real=True,
            identificacao_confiavel=True, instante_coleta=AGORA
        )
    assert sessao.receber(amostra("EURUSD", "M5", m5)).estado == "AGUARDAR"
    assert sessao.receber(amostra("GBPUSD", "M15", m15)).estado == "AGUARDAR"
    assert sessao.receber(amostra("EURUSD", "M15", m15)).estado == "AGUARDAR"
    assert sessao.receber(
        Amostra(ativo="EURUSD-OTC", timeframe="M5", estado=EstadoFonte.OTC_IGNORADO)
    ).estado == "OTC ignorado"
