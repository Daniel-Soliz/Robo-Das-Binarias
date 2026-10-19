"""Linhas de tendência a partir de séries simuladas com pivôs progressivos."""

from data_sources.base import Candle
from analysis.trendlines import detectar_linhas


def vela(minimo, maximo):
    abertura = (minimo + maximo) / 2
    return Candle(
        instante=None, abertura=abertura, maxima=maximo,
        minima=minimo, fechamento=abertura, timeframe="M5",
        finalizado=True, preco_real=False, origem="teste"
    )


def test_lta_com_minimas_ascendentes():
    # Mínimas confirmadas em índices 2, 6, 10 e 14.
    baixos = [.36, .30, .20, .32, .42, .36, .24, .37,
              .46, .39, .28, .40, .50, .43, .32, .45, .51]
    serie = [vela(x, x + .25) for x in baixos]
    linhas = detectar_linhas(serie, minimo_toques=3)
    assert any(l.tipo == "LTA" and l.inclinacao > 0 and l.toques >= 3 for l in linhas)


def test_ltb_com_maximas_descendentes():
    altos = [.66, .72, .80, .68, .60, .64, .76, .62,
             .56, .61, .72, .59, .52, .57, .68, .53, .49]
    serie = [vela(x - .25, x) for x in altos]
    linhas = detectar_linhas(serie, minimo_toques=3)
    assert any(l.tipo == "LTB" and l.inclinacao < 0 and l.toques >= 3 for l in linhas)


def test_sem_linha_sem_pivos():
    serie = [vela(i / 100, i / 100 + .1) for i in range(30)]
    assert detectar_linhas(serie) == ()

