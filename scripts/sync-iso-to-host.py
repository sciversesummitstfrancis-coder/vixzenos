#!/usr/bin/env python3
"""Sync the VixzenOS kickstarts with the live host configuration.

The ISO must look and behave like the machine that built it: same icons,
same cursor, same GTK theme, same wallpapers, same extensions enabled.

Usage: python3 scripts/sync-iso-to-host.py [--apply]
       (default: report the differences only)
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KS = [REPO / "packaging" / "vixzenos.ks",
      REPO / "packaging" / "vixzenos-edu.ks"]


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
        import ast
        return sorted(ast.literal_eval(out))
    except Exception:
        return sorted(x.strip().strip("'") for x in out.split(",") if x.strip())


def current_iso_extensions(ks):
    m = re.search(r"enabled-extensions=\[(.*?)\]", ks.read_text())
    if not m:
        return []
    try:
        import ast
        return sorted(ast.literal_eval("[" + m.group(1) + "]"))
    except Exception:
        return sorted(x.strip().strip("'") for x in m.group(1).split(",")
                      if x.strip())


def main():
    apply = "--apply" in sys.argv
    host_exts = host_extensions()
    host_icon = host_gsettings("org.gnome.desktop.interface", "icon-theme")
    host_cursor = host_gsettings("org.gnome.desktop.interface", "cursor-theme")
    host_gtk = host_gsettings("org.gnome.desktop.interface", "gtk-theme")

    for ks in KS:
        txt = ks.read_text()
        iso_exts = current_iso_extensions(ks)
        missing = [e for e in host_exts if e not in iso_exts]
        extra = [e for e in iso_exts if e not in host_exts]
        print(f"== {ks.name}")
        print(f"   host icon={host_icon} cursor={host_cursor} gtk={host_gtk}")
        print(f"   missing from ISO: {missing or 'none'}")
        print(f"   extra in ISO    : {extra or 'none'}")
        if apply and (missing or extra):
            new = ", ".join(f"'{e}'" for e in host_exts)
            txt = re.sub(r"enabled-extensions=\[.*?\]",
                         f"enabled-extensions=[{new}]", txt, count=1)
            if host_cursor and "cursor-theme=" in txt:
                txt = re.sub(r"cursor-theme='[^']*'",
                             f"cursor-theme='{host_cursor}'", txt, count=1)
            if host_icon and "icon-theme=" in txt:
                txt = re.sub(r"icon-theme='[^']*'",
                             f"icon-theme='{host_icon}'", txt, count=1)
            ks.write_text(txt)
            print("   -> synced")
        else:
            print("   (report only)")


if __name__ == "__main__":
    main()
