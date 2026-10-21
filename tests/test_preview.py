"""Smoke tests for VixzenOS preview (no display needed for --smoke path)."""
import subprocess, sys, pathlib
SRC = pathlib.Path(__file__).resolve().parents[1] / "preview" / "src" / "vixzen_preview.py"

def test_smoke():
    r = subprocess.run([sys.executable, str(SRC), "--smoke"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "smoke OK" in r.stdout
