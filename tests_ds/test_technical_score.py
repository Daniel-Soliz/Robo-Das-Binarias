from types import SimpleNamespace
from ds_trader.technical_score import score_visual


def reading(**kw):
    params=dict(valid_roi=True,stale_frame=False,identity_required=True,
        identity_confirmed=True,next_visual_bias="ALTA",trend_visual="ALTA",
        lta=(0.2,0.3),ltb=None,patterns=("Engolfo de alta",),
        visual_reasons=("Impulso recente de alta",))
    params.update(kw)
    return SimpleNamespace(**params)


def test_confluence_never_claims_percentage_if_identity_is_not_confirmed():
    assert score_visual(reading(identity_confirmed=False)) is None
    assert score_visual(reading(stale_frame=True)) is None
    assert score_visual(reading(valid_roi=False)) is None
    assert score_visual(reading(next_visual_bias="INDEFINIDO")) is None


def test_valid_structure_returns_only_share_of_considered_criteria():
    result=score_visual(reading())
    assert result.alta == 100
    assert result.baixa == 0
    assert result.factors == 4
    assert not hasattr(result,"probability")
    assert not hasattr(result,"win_rate")


def test_insufficient_factors_do_not_produce_false_certainty():
    assert score_visual(reading(lta=None,patterns=(),visual_reasons=())) is None


def test_opposing_votes_reflected_without_claming_prediction():
    result=score_visual(reading(ltb=(0.6,0.5),patterns=("Engolfo de baixa",)))
    assert 0 < result.alta < 100
    assert result.alta+result.baixa == 100
