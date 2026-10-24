"""The Windows builder and CI must execute pytest functions, not skip them."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_ci_jobs_invoke_the_pytest_suite():
    build = (ROOT / "scripts" / "build.ps1").read_text(encoding="utf-8")
    ci = (ROOT / ".github" / "workflows" / "testes.yml").read_text(encoding="utf-8")
    requirements = ROOT / "requirements-test.txt"
    assert requirements.exists()
    assert "pytest==" in requirements.read_text(encoding="utf-8")
    assert "python-dotenv==" in requirements.read_text(encoding="utf-8")
    assert "opencv-python-headless==" in requirements.read_text(encoding="utf-8")
    assert "numpy==" in requirements.read_text(encoding="utf-8")
    assert "pip install -r requirements-test.txt" in build
    assert "pip install -r requirements-test.txt" in ci
    assert "python -m pytest -q -rs" in build
    assert "python -m pytest -q -rs" in ci
    assert "python -m pytest -q -rs tests_ds" not in build
    assert "python -m pytest -q -rs tests_ds" not in ci
    assert "os: [windows-2022]" in ci
