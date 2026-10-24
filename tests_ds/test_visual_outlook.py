"""Cenarios comparativos: nunca percentuais, nunca ordens reais."""
from dataclasses import replace
from types import SimpleNamespace
from unittest import TestCase

from ds_trader.live_screen import VisualCandle
from ds_trader.visual_outlook import compare_visual_scenarios


def candles(step=0.02):
    result = []
    for i in range(30):
        close = .15 + i * step if step > 0 else .85 + i * step
        result.append(VisualCandle(i, close + .016, close - .016,
                                   close - .006 if step > 0 else close + .006,
                                   close, "ALTA" if step > 0 else "BAIXA"))
    return result


def opinion(trend, lta=None, ltb=None):
    return SimpleNamespace(trend=trend, lta=lta, ltb=ltb)


class VisualOutlookTests(TestCase):
    def test_favors_upward_structure_without_opposing_ceiling(self):
        result = compare_visual_scenarios(candles(), opinion("ALTA", lta=(.5, .6)))
        self.assertEqual(result.direction, "ALTA")
        self.assertTrue(result.recent_top > result.recent_bottom)

    def test_favors_downward_structure_without_opposing_floor(self):
        result = compare_visual_scenarios(candles(-.02), opinion("BAIXA", ltb=(.5, .4)))
        self.assertEqual(result.direction, "BAIXA")

    def test_uptrend_near_previous_high_must_abstain(self):
        data = candles()
        previous = data[-2]
        # Ultima barra fica sob uma maxima anterior, mesmo com tendencia alta.
        data[-2] = replace(previous, high=data[-1].close + .012)
        result = compare_visual_scenarios(data, opinion("ALTA", lta=(.5, .6)))
        self.assertEqual(result.direction, "INDEFINIDO")
        self.assertTrue(any("topo recente" in reason for reason in result.reasons))

    def test_short_or_flat_context_is_indefinite(self):
        result = compare_visual_scenarios(candles()[:12], opinion("ALTA"))
        self.assertEqual(result.direction, "INDEFINIDO")
        self.assertNotIn("%", " ".join(result.reasons))
