"""Faixas de reação por máximas/mínimas locais, não linhas arbitrárias."""

from data_sources.base import Candle
from analysis.levels import detectar_pivos, detectar_zonas, perto_de_zona


def vela(centro, amplitude=.02):
    return Candle(
        instante=None, abertura=centro, maxima=centro + amplitude,
        minima=centro - amplitude, fechamento=centro,
        timeframe="M5", finalizado=True, preco_real=False, origem="teste",
    )


def test_pivos_e_zonas_com_toques_repetidos():
    centros = [
        .55, .52, .48, .52, .56, .53, .48, .54, .57, .53,
        .48, .52, .56, .53, .48, .52, .58,
    ]
    serie = [vela(v) for v in centros]
    pivos = detectar_pivos(serie)
    assert sum(p.tipo == "suporte" for p in pivos) >= 3
    zonas = detectar_zonas(serie, minimo_toques=3, tolerancia=.007)
    suportes = [z for z in zonas if z.tipo == "suporte"]
    assert suportes
    assert suportes[0].toques >= 3
    assert perto_de_zona(.46, suportes[0], margem=.001)
    assert not perto_de_zona(.7, suportes[0])


def test_zona_nao_surge_de_um_unico_toque():
    serie = [vela(v) for v in [.60, .55, .50, .55, .60, .62, .64, .66]]
    assert not any(z.tipo == "suporte" for z in detectar_zonas(serie))

