"""Tests for the vix command center (headless; plain asserts, no pytest needed)."""
import subprocess
import sys
import pathlib

VIX = pathlib.Path(__file__).resolve().parents[1] / "apps" / "command-center" / "vix"


def run(*args):
    return subprocess.run([sys.executable, str(VIX), *args],
                          capture_output=True, text=True, timeout=60)


def test_help():
    r = run("help")
    assert r.returncode == 0, r.stderr
    assert "Vixzen Command Center" in r.stdout or "usage" in r.stdout.lower()


def test_version():
    r = run("version")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().startswith("vix ")


def test_system_info():
    r = run("system", "info")
    assert r.returncode == 0, r.stderr
    assert "Vixzen System" in r.stdout


def test_system_info_json():
    import json
    r = run("system", "info", "--json")
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert "cpu" in d and "mem_total" in d


def test_system_status():
    r = run("system", "status")
    assert r.returncode == 0, r.stderr
    assert "Vixzen Status" in r.stdout


def test_doctor():
    r = run("doctor")
    assert r.returncode in (0, 1, 2), r.stderr
    assert "Overall health" in r.stdout


def test_doctor_json():
    import json
    r = run("doctor", "--json")
    assert r.returncode in (0, 1, 2), r.stderr
    d = json.loads(r.stdout)
    assert d["overall"] in ("GOOD", "FAIR", "POOR")
    assert isinstance(d["checks"], list) and d["checks"]


def test_theme_glass():
    for args in (("theme", "list"), ("glass", "status")):
        r = run(*args)
        assert r.returncode == 0, (args, r.stderr)


def test_update_subcommands():
    for args in (("update", "check"), ("update", "history")):
        r = run(*args)
        assert r.returncode in (0, 1, 2), (args, r.stderr)
        assert "Vixzen Update" in r.stdout


def test_update_json():
    import json
    r = run("update", "check", "--json")
    assert r.returncode in (0, 1, 2), r.stderr
    d = json.loads(r.stdout)
    assert "channel" in d and "message" in d


def test_unknown():
    r = run("frobnicate")
    assert r.returncode != 0


if __name__ == "__main__":
    test_help()
    test_version()
    test_system_info()
    test_system_info_json()
    test_system_status()
    test_doctor()
    test_doctor_json()
    test_theme_glass()
    test_update_subcommands()
    test_update_json()
    test_unknown()
    print("vix tests OK: 11 checks passed")
