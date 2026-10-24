"""Regression checks for the optional local M5 asset OCR installation path."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_declares_python_ocr_bridge():
    requirements = (ROOT / "requirements-runtime.txt").read_text(encoding="utf-8")
    assert "pytesseract==0.3.13" in requirements


def test_windows_build_collects_ocr_module():
    build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
    assert "--collect-submodules pytesseract" in build
