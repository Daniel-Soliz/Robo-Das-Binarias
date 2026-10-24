"""Use the OCR binary bundled with the Windows build when available.

Development installs may still use Tesseract installed on the system. The
packaged build includes its own executable and English model files.
"""
from __future__ import annotations

from pathlib import Path
import sys


def configure_tesseract(pytesseract_module, *, bundle_root: Path | None = None) -> bool:
    if bundle_root is None:
        if not getattr(sys, "frozen", False):
            return False
        bundle_root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent / "_internal"))

    folder = Path(bundle_root) / "tesseract"
    binary = folder / "tesseract.exe"
    model = folder / "tessdata" / "eng.traineddata"
    if not binary.is_file() or not model.is_file():
        return False
    pytesseract_module.pytesseract.tesseract_cmd = str(binary)
    return True
