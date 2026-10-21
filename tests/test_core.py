"""Tests for vixzen_core (headless; plain asserts, no pytest needed)."""
import json
import os
import sys

HERE = pathlib = __import__("pathlib").Path(__file__).resolve()
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "shared"))
sys.path.insert(0, str(REPO / "preview" / "src"))

import vixzen_core
from vixzen_core import config


def _isolated_home(monkey=None):
    import tempfile
    tmp = tempfile.mkdtemp(prefix="vixzen-test-home-")
    os.environ["HOME"] = tmp
    import importlib
    importlib.reload(config)
    return tmp


def test_config_roundtrip():
    home = _isolated_home()
    assert config.load("ut", {"a": 1}) == {"a": 1}
    config.save("ut", {"a": 2, "b": "x"})
    assert config.load("ut", {"a": 1}) == {"a": 2, "b": "x"}
    assert os.path.isfile(os.path.join(home, ".config", "vixzen", "ut.json"))


def test_config_corrupt_safe():
    _isolated_home()
    p = config.path("ut2")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write("{not json")
    assert config.load("ut2", {"a": 1}) == {"a": 1}
    assert os.path.isfile(p + ".corrupt-bak")


def test_css_matrix():
    from design import ACCENTS, PERF_MODES, WALLPAPERS, css_for
    assert set(PERF_MODES) == {"saver", "balanced", "enhanced", "insane"}
    assert len(ACCENTS) >= 4 and len(WALLPAPERS) >= 5
    for perf in PERF_MODES:
        for accent in ACCENTS:
            css = css_for("dark", perf, "Neon Burst", accent)
            assert "transition-duration" in css
    assert "600ms" in css_for("dark", "insane", "Deep Night")
    assert "0ms" in css_for("dark", "saver", "Deep Night")


def test_style_headless():
    # provider_for needs Gtk (present) but no display assertions here;
    # apply_display must return False (not crash) without a display.
    from vixzen_core import style
    assert style.apply_display(object()) is False


def test_exports():
    for name in ("load", "save", "path", "provider_for", "refresh",
                 "apply_display", "inform"):
        assert name in vixzen_core.__all__
        assert hasattr(vixzen_core, name)


if __name__ == "__main__":
    test_config_roundtrip()
    test_config_corrupt_safe()
    test_css_matrix()
    test_style_headless()
    test_exports()
    print("core tests OK: 5 checks passed")
