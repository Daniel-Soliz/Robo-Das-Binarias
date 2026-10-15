"""Padrões sintéticos independentes de API, OCR ou plataforma."""

from data_sources.base import Candle
from analysis.patterns import detectar_padroes


def vela(abertura, maxima, minima, fechamento):
    return Candle(
        instante=None, abertura=abertura, maxima=maxima, minima=minima,
        fechamento=fechamento, timeframe="M5", finalizado=True,
        preco_real=False, origem="teste",
    )


def nomes(*velas):
    return {item.nome for item in detectar_padroes(velas)}


def test_engolfos():
    assert "engolfo de alta" in nomes(
        vela(.7, .75, .45, .5), vela(.48, .82, .46, .78)
    )
    assert "engolfo de baixa" in nomes(
        vela(.5, .75, .45, .7), vela(.72, .74, .38, .40)
    )


def test_haramis():
    assert "harami de alta" in nomes(
        vela(.9, .95, .35, .4), vela(.5, .63, .48, .6)
    )
    assert "harami de baixa" in nomes(
        vela(.3, .85, .25, .8), vela(.7, .72, .56, .6)
    )


def test_pinbar_e_doji():
    assert "martelo" in nomes(vela(.5, .62, .1, .6))
    assert "estrela cadente" in nomes(vela(.5, .9, .49, .6))
    assert "doji" in nomes(vela(.5, .9, .1, .51))


def test_estrelas_e_tres_soldados():
    assert "estrela da manhã" in nomes(
        vela(.9, .95, .4, .45),
        vela(.44, .55, .39, .46),
        vela(.46, .87, .44, .8),
    )
    assert "estrela da noite" in nomes(
        vela(.3, .8, .25, .75),
        vela(.74, .78, .67, .72),
        vela(.72, .74, .27, .3),
    )
    assert "três soldados brancos" in nomes(
        vela(.2, .41, .18, .40), vela(.4, .61, .38, .6),
        vela(.6, .81, .58, .8)
    )


def test_ignorar_velas_abertas():
    ultima = vela(.48, .82, .46, .78)
    ultima = Candle(
        instante=None, abertura=ultima.abertura, maxima=ultima.maxima,
        minima=ultima.minima, fechamento=ultima.fechamento,
        timeframe="M5", finalizado=False, preco_real=False, origem="teste"
    )
    assert "engolfo de alta" not in nomes(vela(.7, .75, .45, .5), ultima)
