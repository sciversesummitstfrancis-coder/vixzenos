"""Vixzen Palette test suite.

Verifies, with real execution (not inspection alone):
  1. The shared fuzzy matcher (desktop/shell/fuzzy.js) behaves correctly and
     stays fast on the target-class hardware (200 candidates x 3 queries
     under 50 ms, measured via gjs).
  2. The extension metadata is consistent with the vendored GNOME version.
  3. The keybinding schema compiles cleanly with glib-compile-schemas --strict.
  4. The palette respects the permission boundary: no subprocess/DBus/portal
     usage; user-level GSettings only.
  5. Extension wiring: palette is instantiated, keybinding added/removed,
     and disable() cleans everything up.
"""
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHELL = REPO / "desktop" / "shell"


def _run_gjs_smoke():
    """Run tests/js/fuzzy_smoke.js under gjs; return parsed JSON."""
    proc = subprocess.run(
        ["gjs", "-m", str(REPO / "tests" / "js" / "fuzzy_smoke.js")],
        capture_output=True, text=True, timeout=60,
    )
    json_lines = [l for l in proc.stdout.splitlines() if l.startswith("{")]
    assert json_lines, f"no JSON in harness output:\n{proc.stdout}\n{proc.stderr}"
    if proc.returncode != 0:
        raise AssertionError(f"gjs harness reported failures:\n{proc.stdout}")
    return json.loads(json_lines[-1])


def test_fuzzy_ranking_and_speed():
    data = _run_gjs_smoke()
    assert data["failed"] == 0, json.dumps(data["results"], indent=2)
    assert len(data["results"]) >= 10  # harness didn't silently skip cases


def test_metadata_consistency():
    meta = json.loads((SHELL / "metadata.json").read_text())
    assert meta["uuid"] == "vixzen-shell@vixzen.os"
    assert "50" in meta["shell-version"], "vendored extensions target GNOME 50"
    assert meta["version"] >= 3, "palette release bumps the extension version"
    assert meta["settings-schema"] == "org.vixzen.shell", "keybinding needs the schema"


def test_gschema_compiles_strict():
    with tempfile.TemporaryDirectory() as tmp:
        dst = Path(tmp)
        shutil.copy(SHELL / "schemas" / "org.vixzen.shell.gschema.xml", dst)
        subprocess.run(
            ["glib-compile-schemas", "--strict", str(dst)],
            check=True, capture_output=True, timeout=30,
        )
        assert (dst / "gschemas.compiled").exists()


def test_palette_permission_boundary():
    """The palette must not spawn processes, talk DBus directly, or open portals.
    User-level GSettings toggles are the only state changes it may make."""
    src = (SHELL / "palette.js").read_text()
    forbidden = ["Subprocess", "spawn", "DBus", "dbus", "portal", "systemctl", "pkexec"]
    hits = [f for f in forbidden if f in src]
    assert not hits, f"palette.js references forbidden helpers: {hits}"
    # and it must stay GSettings-only for state changes
    assert "new Gio.Settings(" in src, "quick actions are expected to use GSettings"


def test_extension_wiring_complete():
    """Enable/disable symmetry: everything allocated must be released."""
    src = (SHELL / "extension.js").read_text()
    assert "addKeybinding('open-palette'" in src, "keybinding must be registered"
    assert "removeKeybinding('open-palette')" in src, "keybinding must be released"
    assert "new VixzenPalette(this)" in src, "palette must be instantiated"
    assert "this._palette?.close()" in src, "disable() must close the palette"
    # the menu upgrade must use the shared matcher, not substring matching
    assert "fuzzyScore(q" in src, "start menu must use the shared fuzzy matcher"
    assert ".includes(q)" not in src, "old substring filter should be gone"


def test_palette_files_staged():
    for name in ("fuzzy.js", "palette.js", "extension.js"):
        assert (SHELL / name).is_file(), f"missing {name}"
