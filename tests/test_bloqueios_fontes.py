"""Testes de bloqueio da captura OTC sem comunicação com a plataforma."""

import sys
from types import SimpleNamespace

import numpy as np

from config import Configuracao, Regiao
from data_sources.api_source import ApiSource
from data_sources.base import EstadoFonte
from data_sources.screen_source import ScreenSource


def test_api_ignora_otc_antes_de_conectar(monkeypatch):
    monkeypatch.setattr("data_sources.api_source.load_dotenv", lambda: None)
    fonte = ApiSource(Configuracao(api_ativo="EURUSD-OTC"))
    recebidos = []
    fonte._executar(recebidos.append)
    assert len(recebidos) == 1
    assert recebidos[0].estado is EstadoFonte.OTC_IGNORADO
    assert recebidos[0].candles == ()


def test_tela_otc_nao_le_a_area_do_grafico(monkeypatch):
    class CapturaFalsa:
        def __init__(self):
            self.regioes = []

        def __enter__(self):
            return self

        def __exit__(self, *_argumentos):
            return None

        def grab(self, regiao):
            self.regioes.append(regiao)
            return np.zeros((30, 120, 4), dtype=np.uint8)

    captura = CapturaFalsa()
    monkeypatch.setitem(sys.modules, "mss", SimpleNamespace(mss=lambda: captura))
    monkeypatch.setattr(
        "data_sources.screen_source.extrair_texto",
        lambda _imagem: "EUR/USD OTC M5",
    )
    config = Configuracao(
        regiao_grafico=Regiao(0, 0, 300, 120),
        regiao_cabecalho=Regiao(0, 0, 120, 30),
    )
    fonte = ScreenSource(config)
    recebidos = []

    def receber(amostra):
        recebidos.append(amostra)
        fonte._parar.set()

    fonte._executar(receber)
    assert len(captura.regioes) == 1  # Apenas cabeçalho; nenhuma leitura do gráfico.
    assert recebidos[0].estado is EstadoFonte.OTC_IGNORADO
    assert recebidos[0].candles == ()

