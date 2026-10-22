"""Testa equivalência do reconhecedor rápido com o legado, sem conexão com corretora."""
import sys
import threading
import time
import unittest
from queue import Queue
from unittest.mock import patch

from PIL import Image, ImageDraw

from ds_trader.live_screen import (
    Region, ScreenMonitor, assess, detect_visual_candles, _model_width,
)


def chart(width=750, height=330, count=32, adjacent=False):
    im = Image.new("RGB", (width, height), "#101b2d")
    draw = ImageDraw.Draw(im)
    spacing = max(12, min(24, (width - 40) // count))
    for i in range(count):
        x = 15 + spacing * i
        is_red = i % 2 == 1 if adjacent else i % 3 == 0
        color = "#ef4b63" if is_red else "#28c891"
        y = 110 + (i % 6) * 9
        draw.line((x + 4, y-12, x + 4, y+34), fill=color, width=1)
        draw.rectangle((x, y, x + 9, y + 22), fill=color)
    return im


class FastDetectionTests(unittest.TestCase):
    def test_numpy_matches_legacy_on_regular_and_alternating_candles(self):
        try:
            import numpy  # noqa F401
        except ImportError:
            self.skipTest("NumPy opcional fora do Windows")
        for size, count, adjacent in (
            ((750, 330), 32, False),
            ((750, 330), 30, True),
            ((1600, 900), 32, True),
            ((360, 740), 25, True),
        ):
            with self.subTest(size=size, count=count, adjacent=adjacent):
                img = chart(*size, count=count, adjacent=adjacent)
                fast = detect_visual_candles(img)
                # Força o fallback, preservando o módulo externo intacto.
                with patch.dict(sys.modules, {"ds_trader.visual_fast": None}):
                    slow = detect_visual_candles(img)
                self.assertEqual(fast, slow)
                self.assertFalse(assess(img).trading_signal)

    def test_blank_screenshot_never_generates_call_or_put(self):
        self.assertEqual(detect_visual_candles(Image.new("RGB", (720, 400), "#101724")), ())
        self.assertEqual(assess(Image.new("RGB", (720, 400))).bias, "AGUARDAR")

    def test_model_width_respects_tall_roi(self):
        self.assertEqual(_model_width(Image.new("RGB", (750, 330))), 750)
        self.assertEqual(_model_width(Image.new("RGB", (2400, 800))), 1200)
        self.assertEqual(_model_width(Image.new("RGB", (500, 1000))), 350)

    def test_latest_frame_queue_drops_obsolete_frames(self):
        monitor = ScreenMonitor(Region(0, 0, 600, 300), interval_seconds=.65)
        for i in range(100):
            monitor._put_latest(monitor._frames, (i, 300, b""))
        self.assertEqual(monitor._frames.qsize(), 1)
        self.assertEqual(monitor._frames.get_nowait()[0], 99)

    def test_ui_can_request_stop_without_waiting_for_slow_worker(self):
        monitor = ScreenMonitor(Region(0, 0, 600, 300), interval_seconds=.65)
        started = threading.Event()
        release = threading.Event()

        def slow_worker():
            started.set()
            release.wait(2)

        try:
            monitor._thread = threading.Thread(target=slow_worker, daemon=True)
            monitor._thread.start()
            self.assertTrue(started.wait(1))
            begin = time.monotonic()
            monitor.stop(wait=False)
            self.assertLess(time.monotonic() - begin, .3)
            self.assertTrue(monitor._stop.is_set())
        finally:
            release.set()
            monitor._thread.join(1)


if __name__ == "__main__":
    unittest.main()
