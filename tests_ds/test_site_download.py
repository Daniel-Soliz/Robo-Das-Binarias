"""The public download page offers the installer, not source archives."""
from pathlib import Path


def test_site_points_only_to_validated_exe_release_asset():
    source = (Path(__file__).resolve().parents[1] / "index.html").read_text("utf-8")
    assert "releases/latest" in source
    assert "DS-Trader-Setup.exe" in source
    assert "if (!exe)" in source
    assert 'id="portable"' not in source
    assert "const zip = find(" not in source
