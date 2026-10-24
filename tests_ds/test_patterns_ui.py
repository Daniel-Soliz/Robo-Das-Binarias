"""Nova aba compartilha a captura; dados insuficientes nunca geram previsões falsas."""
from types import SimpleNamespace
from ds_trader.patterns_ui import reading_for


def test_no_live_image_yields_wait():
    state = reading_for(None, active=True)
    assert state.state == "AGUARDAR"
    assert state.patterns == ()


def test_otc_is_only_labeled_after_confirmed_identity():
    result = SimpleNamespace(stale_frame=False, valid_roi=True, asset="EUR/USD",
                             asset_otc=True, identity_confirmed=True,
                             next_visual_bias="ALTA", patterns=("Martelo",),
                             structures=("LTA",), visual_reasons=("Fundos ascendentes",))
    state = reading_for(result, active=True)
    assert state.asset == "EUR/USD (OTC)"
    assert state.visual == "ALTA VISUAL"
    assert state.state == "VISUAL · NÃO VALIDADO"
    result.identity_confirmed = False
    assert reading_for(result, active=True).asset == "Ativo não confirmado"
    result.stale_frame = True
    assert reading_for(result, active=True).patterns == ()


def test_no_displayed_fake_win_rate():
    state = reading_for(None, active=False)
    assert not hasattr(state, "probability")
    assert not hasattr(state, "win_rate")
