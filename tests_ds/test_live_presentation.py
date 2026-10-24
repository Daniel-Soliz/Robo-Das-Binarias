"""Sem acesso à tela, comprovam estados seguros do painel lateral."""
from dataclasses import replace
from unittest import TestCase

from ds_trader.live_screen import Assessment, Region
from ds_trader.live_presentation import presentation_for, screen_region_is_obscured


class ScreenPanelTest(TestCase):
    def sample(self, **kwargs):
        a = Assessment(
            captured_at="2026-10-20T12:00:00+00:00", detected=40,
            completed_estimate=39, movement="Alta visual relativa",
            explanation="Engolfo de alta; hipótese não validada.",
            bias="CALL", patterns=("Engolfo de alta",),
            structures=("LTA", "Suporte relativo"), valid_roi=True,
            temporal_verified=True,
        )
        return replace(a, **kwargs)

    def test_direction_is_only_an_experimental_hypothesis(self):
        state = presentation_for(self.sample())
        self.assertEqual(state.side, "CALL")
        self.assertEqual(state.tone, "up")
        self.assertIn("EXPERIMENTAL", state.subtitle)
        self.assertIn("Engolfo", state.pattern)
        self.assertIn("LTA", state.structure)

    def test_put_is_distinct(self):
        state = presentation_for(self.sample(bias="PUT"))
        self.assertEqual(state.side, "PUT")
        self.assertEqual(state.tone, "down")

    def test_insufficient_recognition_forces_wait(self):
        state = presentation_for(self.sample(bias="CALL", valid_roi=False))
        self.assertEqual(state.side, "AGUARDAR")
        self.assertIn("LEITURA INSUFICIENTE", state.subtitle)

    def test_temporal_confirmation_missing_blocks_call_and_put(self):
        for side in ("CALL", "PUT"):
            state = presentation_for(self.sample(bias=side, temporal_verified=False))
            self.assertEqual(state.side, "AGUARDAR")
            self.assertIn("NAO VERIFICADOS", state.subtitle)
            self.assertIn("LTA", state.structure)

    def test_trend_can_be_shown_without_issuing_trade_signal(self):
        state = presentation_for(self.sample(temporal_verified=False, trend_visual="ALTA"))
        self.assertEqual(state.side, "AGUARDAR")
        self.assertIn("ALTA", state.status)
        self.assertIn("Tendência visual: ALTA", state.structure)

    def test_visual_scenario_does_not_unlock_call(self):
        result = self.sample(temporal_verified=False, next_visual_bias="ALTA",
                             visual_reasons=("Fundos ascendentes",))
        state = presentation_for(result)
        self.assertEqual(state.side, "AGUARDAR")
        self.assertEqual(state.outlook, "ALTA FAVORECIDA")
        self.assertIn("Fundos ascendentes", state.outlook_reason)

    def test_obscured_chart_hides_prior_visual_bias(self):
        result = self.sample(next_visual_bias="BAIXA")
        state = presentation_for(result, obscured=True)
        self.assertEqual(state.outlook, "SEM VANTAGEM CLARA")

    def test_unknown_window_asset_hides_directional_visual_forecast(self):
        result = self.sample(identity_required=True, identity_confirmed=False,
                             next_visual_bias="ALTA", temporal_verified=False)
        state = presentation_for(result)
        self.assertEqual(state.side, "AGUARDAR")
        self.assertEqual(state.outlook, "SEM VANTAGEM CLARA")
        self.assertIn("ATIVO", state.subtitle)

    def test_obscured_source_forces_wait_even_with_call(self):
        state = presentation_for(self.sample(), obscured=True)
        self.assertEqual(state.side, "AGUARDAR")
        self.assertIn("ENCOBERTO", state.subtitle)
        self.assertIn("Mova o DS Trader", state.status)

    def test_unrecognized_bias_never_becomes_an_order(self):
        state = presentation_for(self.sample(bias="COMPRAR AGORA"))
        self.assertEqual(state.side, "AGUARDAR")

    def test_overlay_geometry_with_virtual_desktop_coordinates(self):
        chart = Region(0, 0, 700, 400)
        self.assertTrue(screen_region_is_obscured(chart, (10, 10, 400, 300)))
        self.assertFalse(screen_region_is_obscured(chart, (720, 10, 600, 700)))
        self.assertFalse(screen_region_is_obscured(chart, (698, 100, 100, 200)))
        left = Region(-950, 50, 750, 300)
        self.assertTrue(screen_region_is_obscured(left, (-700, 50, 800, 300)))
        self.assertFalse(screen_region_is_obscured(left, (0, 0, 600, 400)))
