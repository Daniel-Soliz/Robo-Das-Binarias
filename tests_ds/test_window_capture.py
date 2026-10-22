"""Testes de captura de janela fixada sem precisar de Windows nem corretora."""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from ds_trader.live_screen import Region, ScreenMonitor, crop_window_image
from ds_trader.window_capture import (WindowInfo, WindowTarget, WindowCaptureError,
                                      choose_window_for_region, enumerate_windows)


class WindowSelectionTests(unittest.TestCase):
    @unittest.skipUnless(sys.platform == "win32", "EnumWindows so existe no Windows")
    def test_real_win32_api_can_list_windows_without_capture(self):
        self.assertIsInstance(enumerate_windows(), list)

    def test_selects_underlying_foreign_window_not_own_overlay(self):
        region = Region(210, 180, 600, 330)
        windows = [
            WindowInfo(101, 999, "DS Trader (overlay)", (0, 0, 1100, 800)),
            WindowInfo(102, 222, "", (0, 0, 1100, 800)),
            WindowInfo(103, 333, "Navegador - Grafico", (100, 100, 1000, 700)),
            WindowInfo(104, 444, "Outra janela atras", (0, 0, 1000, 700)),
        ]
        target = choose_window_for_region(region, windows, own_pid=999)
        self.assertEqual(target.hwnd, 103)
        self.assertEqual(target.crop, (110, 80, 710, 410))

    def test_rejects_region_crossing_target_window_and_non_windows(self):
        windows = [WindowInfo(123, 456, "Navegador", (0, 0, 800, 600))]
        with self.assertRaises(WindowCaptureError):
            choose_window_for_region(Region(700, 100, 300, 200), windows, own_pid=999)
        with self.assertRaises(WindowCaptureError):
            choose_window_for_region(Region(0, 0, 700, 400), [], own_pid=999)

    def test_crop_tracks_window_not_desktop_coordinates(self):
        target = WindowTarget(123, 456, "Grafico", (100, 100, 1100, 700),
                              (200, 120, 900, 530))
        frame = Image.new("RGB", (1000, 600), "#101820")
        region = crop_window_image(frame, target)
        self.assertEqual(region.size, (700, 410))
        # Escala DPI uniforme; o recorte continua relativo ao alvo.
        scaled = crop_window_image(Image.new("RGB", (1250, 750)), target)
        self.assertEqual(scaled.size, (875, 512))
        with self.assertRaises(WindowCaptureError):
            crop_window_image(Image.new("RGB", (1600, 600)), target)


class WindowMonitorTests(unittest.TestCase):
    def test_window_capture_uses_hwnd_not_desktop_and_stays_read_only(self):
        target = WindowTarget(123, 456, "Grafico", (0, 0, 750, 330),
                              (0, 0, 750, 330))
        used = []
        class Controller:
            def is_finished(self):
                return False
            def stop(self):
                pass
        class FakeCapture:
            def __init__(self, **kwargs):
                used.append(kwargs)
            def event(self, callback):
                setattr(self, callback.__name__, callback)
                return callback
            def start_free_threaded(self):
                frame = SimpleNamespace(
                    width=750, height=330,
                    frame_buffer=SimpleNamespace(tobytes=lambda: bytes((12, 20, 30, 255))*750*330),
                )
                self.on_frame_arrived(frame, SimpleNamespace(stop=lambda: None))
                return Controller()
        fake_module = SimpleNamespace(WindowsCapture=FakeCapture)
        monitor = ScreenMonitor(Region(0, 0, 750, 330), window_target=target)
        with patch.dict(sys.modules, {"windows_capture": fake_module}), \
             patch("ds_trader.live_screen.check_target_window"), \
             patch.object(monitor, "_run_desktop", side_effect=AssertionError("desktop usado")):
            monitor.start()
            try:
                result, _frame = monitor.results.get(timeout=5)
                self.assertFalse(result.trading_signal)
                self.assertEqual(result.bias, "AGUARDAR")
            finally:
                monitor.stop()
        self.assertEqual(used[0]["window_hwnd"], 123)
        self.assertFalse(used[0]["cursor_capture"])
        self.assertEqual(used[0]["minimum_update_interval"], 1200)

    def test_missing_window_capture_library_is_error_not_desktop_fallback(self):
        target = WindowTarget(123, 456, "Grafico", (0, 0, 750, 330),
                              (0, 0, 750, 330))
        monitor = ScreenMonitor(Region(0, 0, 750, 330), window_target=target)
        with patch.dict(sys.modules, {"windows_capture": None}), \
             patch.object(monitor, "_run_desktop", side_effect=AssertionError("desktop usado")):
            monitor.start()
            try:
                kind, reason = monitor.results.get(timeout=5)
                self.assertEqual(kind, "error")
                self.assertIn("windows-capture", reason)
            finally:
                monitor.stop()


if __name__ == "__main__":
    unittest.main()
