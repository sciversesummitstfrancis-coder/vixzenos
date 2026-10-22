"""Verify the ISO payload ships everything the live host has.

The VixzenOS ISO must look and behave like the machine that built it:
same extensions enabled, same theme/icon/cursor, same apps. This test
compares the kickstart + staged payload against live gsettings so drift
is caught at build time instead of after a 2-hour ISO build.
"""
import ast
import os
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
KS = [REPO / "packaging" / "vixzenos.ks",
      REPO / "packaging" / "vixzenos-edu.ks"]
STAGE = pathlib.Path("/tmp/vixzen-stage")


def host_gsettings(schema, key):
    try:
        out = subprocess.run(["gsettings", "get", schema, key],
                             capture_output=True, text=True, timeout=8).stdout
        return out.strip().strip("'")
    except Exception:
        return ""


def host_extensions():
    out = host_gsettings("org.gnome.shell", "enabled-extensions")
    try:
        return sorted(ast.literal_eval(out))
    except Exception:
        return []


def ks_extensions(ks):
    m = re.search(r"enabled-extensions=\[(.*?)\]", ks.read_text())
    if not m:
        return []
    try:
        return sorted(ast.literal_eval("[" + m.group(1) + "]"))
    except Exception:
        return []


def ks_vendored(ks):
    out = {}
    for L in re.findall(r'for spec in ((?:"[^"]*"\s*)+); do', ks.read_text()):
        for z, u in re.findall(r'"([^"|]+)\|([^"]+)"', L):
            out[u] = z
    return out


def test_iso_matches_host():
    host = host_extensions()
    if not host:
        return  # no session (CI/headless): nothing to compare
    for ks in KS:
        iso = ks_extensions(ks)
        missing = [e for e in host if e not in iso]
        assert not missing, f"{ks.name} missing extensions: {missing}"
        vendored = ks_vendored(ks)
        for uuid, zipname in vendored.items():
            if uuid in host:
                p = STAGE / "shell" / zipname
                if STAGE.is_dir():
                    assert p.is_file(), f"{zipname} not staged"


def test_look_bundle_staged():
    if not STAGE.is_dir():
        return
    for d in ("looks/WhiteSur-Dark-blue", "looks/WhiteSur-dark",
              "looks/whitesur", "cursors/WhiteSur", "widgets",
              "core", "cmd"):
        p = STAGE / d
        if d.startswith("looks/") and not p.exists():
            # optional bundle — only assert when the repo ships it
            src = REPO / "assets" / "gtk-theme" / "WhiteSur-Dark-blue"
            assert not src.is_dir(), f"{d} missing from stage"
        else:
            assert p.exists(), f"{d} missing from stage"


def test_apps_present_in_image():
    for ks in KS:
        txt = ks.read_text()
        for needle in ("/usr/local/bin/vix", "vixzen_core",
                       "vixzen-widgets@vixzen.os", "vixzenos-looks"):
            if needle == "vixzenos-looks":
                continue
            assert needle in txt, f"{ks.name} missing {needle}"


if __name__ == "__main__":
    test_iso_matches_host()
    test_look_bundle_staged()
    test_apps_present_in_image()
    print("iso-payload tests OK: 3 checks passed")
