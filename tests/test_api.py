"""Validação de candles da API sem credenciais ou acesso à plataforma."""

from data_sources.api_source import converter_candles_api


def teste_dado(inicio, **alteracoes):
    item = {
        "from": inicio, "open": 1.08, "max": 1.1,
        "min": 1.07, "close": 1.09,
    }
    item.update(alteracoes)
    return item


def test_normalizacao_e_fechamento():
    dados = [
        teste_dado(1000), teste_dado(700),
        teste_dado(1000, close=1.095), teste_dado(1300, max=0.5)
    ]
    velas = converter_candles_api(dados, "M5", agora=1250)
    assert len(velas) == 2
    assert velas[0].instante.timestamp() == 700
    assert velas[1].fechamento == 1.095
    assert velas[0].finalizado
    assert not velas[1].finalizado
    assert all(vela.preco_real for vela in velas)


def test_api_nao_aceita_preco_impossivel():
    assert converter_candles_api([teste_dado(1000, min=1.2)], "M5", 1500) == ()
