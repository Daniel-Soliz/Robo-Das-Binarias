"""Identifica uma janela Windows para captura fixa, mesmo se depois for coberta.

Os recortes sao relativos a janela de origem e nao ao desktop. A descoberta
automatica so considera janelas chamadas IQ Option e nunca captura a conta.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
import sys


class WindowCaptureError(RuntimeError):
    pass


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    pid: int
    title: str
    bounds: tuple[int, int, int, int]  # left, top, right, bottom


@dataclass(frozen=True)
class WindowTarget:
    hwnd: int
    pid: int
    title: str
    bounds: tuple[int, int, int, int]
    crop: tuple[int, int, int, int]  # coordenadas locais de origem


def auto_target_for_window(window: WindowInfo):
    """Propose a conservative central chart ROI; never certify it as correct.

    The central crop intentionally excludes the sidebar/toolbars. The visual
    analyzer must still reject illegible regions and uncertain timestamps.
    """
    from ds_trader.live_screen import Region

    if (window.hwnd <= 0 or window.pid <= 0 or
            not re.match(r"^\s*IQ[\s-]*Option\b", window.title, re.IGNORECASE)):
        return None
    left, top, right, bottom = window.bounds
    width, height = right - left, bottom - top
    if width < 800 or height < 450:
        return None
    crop = (int(width * .14), int(height * .15),
            int(width * .92), int(height * .83))
    x1, y1, x2, y2 = crop
    region = Region(left + x1, top + y1, x2 - x1, y2 - y1)
    return region, WindowTarget(window.hwnd, window.pid, window.title,
                                window.bounds, crop)


class IqOptionDiscovery:
    """Wait for a stable, unique IQ Option window before automatic capture."""

    def __init__(self):
        self._previous = None
        self._streak = 0

    def reset(self):
        self._previous = None
        self._streak = 0

    def observe(self, windows: list[WindowInfo], *, own_pid: int):
        options = [item for window in windows
                   if window.pid != own_pid
                   for item in (auto_target_for_window(window),)
                   if item is not None]
        if len(options) != 1:
            self.reset()
            return None
        region, target = options[0]
        if target.hwnd != self._previous:
            self._previous = target.hwnd
            self._streak = 1
            return None
        self._streak += 1
        return (region, target) if self._streak >= 2 else None


def choose_window_for_region(region, windows: list[WindowInfo], *, own_pid: int) -> WindowTarget:
    """A primeira janela elegivel esta mais a frente na ordem Z do Windows."""
    left, top = region.left, region.top
    right, bottom = left + region.width, top + region.height
    for window in windows:
        wl, wt, wr, wb = window.bounds
        if (window.hwnd <= 0 or window.pid == own_pid or not window.title.strip()
                or wl >= wr or wt >= wb):
            continue
        # A ROI inteira deve pertencer ao alvo, impedindo capturar a area de
        # trabalho / outra aplicacao ou um grafico fora da janela escolhida.
        if wl <= left and wt <= top and right <= wr and bottom <= wb:
            return WindowTarget(window.hwnd, window.pid, window.title, window.bounds,
                                (left - wl, top - wt, right - wl, bottom - wt))
    raise WindowCaptureError(
        "Nenhuma janela identificavel contem todo o recorte. Deixe o aplicativo "
        "da IQ Option com o grafico visivel e selecione apenas a area das velas."
    )


def _win_api():
    if sys.platform != "win32":
        raise WindowCaptureError("Captura de janela fixa requer Windows 10/11.")
    import ctypes
    from ctypes import wintypes

    class RECT(ctypes.Structure):
        _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                    ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    dwmapi.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                             ctypes.c_void_p, wintypes.DWORD]
    dwmapi.DwmGetWindowAttribute.restype = wintypes.LONG
    return ctypes, wintypes, RECT, user32, dwmapi


def _bounds(hwnd, api):
    ctypes, _wintypes, RECT, user32, dwmapi = api
    rectangle = RECT()
    # DWMWA_EXTENDED_FRAME_BOUNDS (9): alinhado ao conteudo capturado pela WGC,
    # sem a borda invisivel que GetWindowRect pode incluir.
    if dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rectangle),
                                    ctypes.sizeof(rectangle)) != 0:
        if not user32.GetWindowRect(hwnd, ctypes.byref(rectangle)):
            return None
    return (rectangle.left, rectangle.top, rectangle.right, rectangle.bottom)


def enumerate_windows() -> list[WindowInfo]:
    ctypes, wintypes, _RECT, user32, _dwmapi = api = _win_api()
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def callback(hwnd, _param):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title, length + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        bounds = _bounds(hwnd, api)
        if bounds:
            found.append(WindowInfo(int(hwnd), int(pid.value), title.value, bounds))
        return True

    user32.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    if not user32.EnumWindows(callback, 0):
        raise WindowCaptureError("Nao foi possivel listar janelas abertas do Windows.")
    return found


def select_window_for_region(region) -> WindowTarget:
    return choose_window_for_region(region, enumerate_windows(), own_pid=os.getpid())


def check_target_window(target: WindowTarget) -> None:
    """Evita HWND reciclado, fechado ou janela minimizada (frame congelado)."""
    ctypes, wintypes, _RECT, user32, _dwmapi = _win_api()
    if not user32.IsWindow(target.hwnd):
        raise WindowCaptureError("A janela fixada foi fechada. Selecione novamente.")
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(target.hwnd, ctypes.byref(pid))
    if pid.value != target.pid:
        raise WindowCaptureError("A janela fixada mudou. Selecione novamente.")
    if user32.IsIconic(target.hwnd):
        raise WindowCaptureError("Janela minimizada. Restaure-a para continuar a captura.")
