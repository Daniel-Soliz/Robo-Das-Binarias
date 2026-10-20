"""Testes deterministas da leitura visual sem permissao para capturar tela real."""
import unittest
import sys
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image, ImageDraw
from dataclasses import replace
from ds_trader.live_screen import Region, ScreenMonitor, detect_visual_candles, assess, annotate_preview


def sample(upward=True, count=18, gap=39):
    image = Image.new("RGB", (750, 330), "#111a26")
    draw = ImageDraw.Draw(image)
    for i in range(count):
        x = 10 + i * gap
        if upward:
            top = 248 - i * (3 if count>20 else 7)
            direction = "#23d18b"
        else:
            top = 35 + i * (3 if count>20 else 7)
            direction = "#f45168"
        draw.line((x+6, top-9, x+6, top+34), fill=direction, width=1)
        draw.rectangle((x, top, x+12, top+19), fill=direction)
    return image


class ScreenGeometryTests(unittest.TestCase):
    def test_valid_region_and_mss_dict(self):
        self.assertEqual(Region(30, 20, 640, 380).mss_rect(),
                         dict(left=30, top=20, width=640, height=380))
        with self.assertRaises(ValueError):
            Region(0, 0, 100, 90)
        with self.assertRaises(ValueError):
            Region(0.2, 0, 400, 300)

    def test_interval_bounds(self):
        with self.assertRaises(ValueError):
            ScreenMonitor(Region(0, 0, 400, 300), interval_seconds=0.1)


class ScreenAnalysisTests(unittest.TestCase):
    def test_white_or_blank_is_never_a_signal(self):
        result = assess(Image.new("RGB", (500, 350), "#101723"))
        self.assertEqual(result.completed_estimate, 0)
        self.assertEqual(result.movement, "Leitura insuficiente")
        self.assertFalse(result.is_market_quote)
        self.assertFalse(result.trading_signal)

    def test_upward_colored_candles(self):
        candles = detect_visual_candles(sample(upward=True))
        self.assertGreaterEqual(len(candles), 12)
        result = assess(sample(upward=True), captured_at="2026-10-19T12:00:00+00:00")
        self.assertEqual(result.captured_at, "2026-10-19T12:00:00+00:00")
        self.assertEqual(result.movement, "Leitura insuficiente")
        self.assertEqual(result.bias, "AGUARDAR")
        self.assertEqual(result.completed_estimate, result.detected - 1)
        self.assertFalse(result.trading_signal)

    def test_downward_colored_candles(self):
        result = assess(sample(upward=False))
        self.assertGreaterEqual(result.completed_estimate, 10)
        self.assertEqual(result.movement, "Leitura insuficiente")
        self.assertFalse(result.is_market_quote)

    def test_regular_chart_enables_structural_analysis_only(self):
        image=sample(upward=True,count=36,gap=20)
        result=assess(image)
        self.assertGreaterEqual(result.detected,26)
        self.assertTrue(result.valid_roi)
        self.assertIn(result.bias,("CALL","PUT","AGUARDAR"))
        self.assertFalse(result.trading_signal)
        self.assertFalse(result.is_market_quote)
        self.assertIn("NAO e sinal validado",result.explanation)

    def test_lta_and_ltb_overlay_are_only_drawn_on_preview_copy(self):
        image=sample(upward=True,count=36,gap=20)
        result=assess(image)
        self.assertTrue(result.valid_roi)
        artificial=replace(result,lta=(.50,.51),ltb=(.62,.61))
        preview=annotate_preview(image,artificial)
        self.assertIsNot(image,preview)
        self.assertNotEqual(preview.tobytes(),image.tobytes())
        no_overlay=replace(result,lta=None,ltb=None)
        self.assertEqual(annotate_preview(image,no_overlay).tobytes(),image.tobytes())

    def test_wrong_roi_rejects_sparse_buttons(self):
        frame=Image.new("RGB",(750,330),"#111a26")
        draw=ImageDraw.Draw(frame)
        for i in range(20):
            x=15+i*31
            draw.rectangle((x,20,x+12,35),fill="#23d18b")
        result=assess(frame)
        self.assertEqual(result.bias,"AGUARDAR")
        self.assertFalse(result.valid_roi)

    def test_monitor_requires_three_stable_frames_before_provisional_bias(self):
        image=sample(upward=True,count=36,gap=20)
        class Capture:
            monitors=[dict(left=0,top=0,width=1200,height=800)]
            def __enter__(self):return self
            def __exit__(self,*_args):return False
            def grab(self,_rect):
                return SimpleNamespace(size=image.size,rgb=image.tobytes())
        monitor=ScreenMonitor(Region(0,0,750,330),interval_seconds=0.5)
        with patch.dict(sys.modules,{"mss":SimpleNamespace(mss=lambda:Capture())}):
            try:
                monitor.start()
                first,_=monitor.results.get(timeout=6)
                second,_=monitor.results.get(timeout=6)
                third,_=monitor.results.get(timeout=6)
                self.assertEqual(first.bias,"AGUARDAR")
                self.assertEqual(second.bias,"AGUARDAR")
                self.assertTrue(third.valid_roi)
                self.assertGreaterEqual(monitor._stable_reads,3)
                self.assertFalse(third.trading_signal)
            finally:
                monitor.stop()

    def test_continuous_capture_with_fake_desktop_stays_local(self):
        image = sample(upward=True)

        class Capture:
            monitors = [dict(left=0, top=0, width=1200, height=800)]
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def grab(self, _rect):
                return SimpleNamespace(size=image.size, rgb=image.tobytes())

        fake_mss = SimpleNamespace(mss=lambda: Capture())
        monitor = ScreenMonitor(Region(20, 10, 750, 330), interval_seconds=0.5)
        with patch.dict(sys.modules, {"mss": fake_mss}):
            try:
                monitor.start()
                result, frame = monitor.results.get(timeout=6)
                self.assertGreaterEqual(result.detected, 10)
                self.assertLessEqual(frame.width, 1050)
                self.assertFalse(result.is_market_quote)
                self.assertFalse(result.trading_signal)
            finally:
                monitor.stop()
        self.assertFalse(monitor.running)

    def test_no_market_price_or_expiry_extracted(self):
        result = assess(sample(upward=True))
        self.assertFalse(hasattr(result, "market_price"))
        self.assertFalse(hasattr(result, "expiry"))
        self.assertIn("Nao existe hipotese segura", result.explanation)


if __name__ == "__main__":
    unittest.main()
