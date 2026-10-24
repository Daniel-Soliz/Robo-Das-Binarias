"""Test a self-contained OCR engine without needing Windows in Linux CI."""
from pathlib import Path
from types import SimpleNamespace



def _engine():
    return SimpleNamespace(pytesseract=SimpleNamespace(tesseract_cmd="tesseract"))


def test_bundled_tesseract_is_selected_only_with_model_file(tmp_path: Path):
    from ds_trader.ocr_runtime import configure_tesseract
    engine = _engine()
    exe = tmp_path / "tesseract" / "tesseract.exe"
    exe.parent.mkdir()
    exe.touch()
    assert configure_tesseract(engine, bundle_root=tmp_path) is False
    assert engine.pytesseract.tesseract_cmd == "tesseract"

    model = tmp_path / "tesseract" / "tessdata" / "eng.traineddata"
    model.parent.mkdir()
    model.touch()
    assert configure_tesseract(engine, bundle_root=tmp_path) is True
    assert engine.pytesseract.tesseract_cmd == str(exe)


def test_build_requires_and_bundles_ocr_files():
    build = (Path(__file__).resolve().parents[1] / "scripts" / "build.ps1").read_text("utf-8")
    assert "tesseract.exe" in build
    assert "eng.traineddata" in build
    assert 'tesseractDir;tesseract' in build
