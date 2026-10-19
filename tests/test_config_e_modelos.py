"""Testes de configuração local e contrato de candles."""

from datetime import datetime, timezone

import pytest

from config import Configuracao, Regiao, carregar_configuracao, salvar_configuracao
from data_sources.base import Candle


def test_config_criada_sem_credenciais(tmp_path):
    caminho = tmp_path / "config.json"
    configuracao = carregar_configuracao(caminho)
    assert configuracao.modo == "tela"
    assert "password" not in caminho.read_text().lower()
    configuracao.regiao_grafico = Regiao(10, 20, 800, 450)
    salvar_configuracao(configuracao, caminho)
    assert carregar_configuracao(caminho).regiao_grafico.width == 800


def test_fps_invalido_e_regiao_invalida():
    with pytest.raises(ValueError):
        Configuracao(captura_fps=100).validar()
    with pytest.raises(ValueError):
        Regiao(1, 2, 0, 3).validar()


def test_candle_invalido():
    dados = dict(
        instante=datetime.now(timezone.utc), abertura=0.4, maxima=0.7,
        minima=0.2, fechamento=0.5, timeframe="M5",
        finalizado=False, preco_real=False, origem="tela"
    )
    Candle(**dados)
    dados["maxima"] = 0.3
    with pytest.raises(ValueError):
        Candle(**dados)

