#!/usr/bin/env python3
"""Recolor the Vixzen icon set to the Neon glow style (green-on-dark).

Geometry, filenames and symlinks untouched — only hex colors remap.
Backup: assets/icons/Vixzen-classic/ (created on first run).
Revert: ./make_vixzen_neon.py --revert
Run: python3 assets/icons/theme/make_vixzen_neon.py [--revert]
"""
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEME = os.path.join(HERE, "Vixzen")
BACKUP = os.path.join(HERE, "..", "Vixzen-classic")

# Indigo/blue/steel -> neon green family. Whites, semantic reds/ambers and
# existing greens stay exactly as they are.
NEON = {
    "#4F46E5": "#00E676", "#7C7CFF": "#6EE7B7",
    "#6BB6FF": "#4ADE80", "#1E6FEB": "#00A651",
    "#174A9E": "#065F46", "#0B3D91": "#052E16",
    "#1D4ED8": "#059669", "#60A5FA": "#6EE7B7",
    "#0891B2": "#00A651", "#06B6D4": "#00E676",
    "#22D3EE": "#A7F3D0", "#0E7490": "#047857",
    "#6D28D9": "#00A651", "#A78BFA": "#6EE7B7",
    "#8B8FA3": "#14532D", "#4A4E69": "#04120A",
    "#3B3F4E": "#052012", "#2B2F3A": "#04120A",
    "#171923": "#020604", "#101218": "#020604",
    "#1E293B": "#052012", "#334155": "#14532D",
    "#64748B": "#86EFAC", "#D4D8E3": "#D1FAE5",
    "#DCE3F0": "#D1FAE5", "#C9D6F2": "#D1FAE5",
}


def main():
    if "--revert" in sys.argv:
        assert os.path.isdir(BACKUP), "no backup found"
        shutil.rmtree(THEME)
        shutil.copytree(BACKUP, THEME, symlinks=True)
        print("reverted to classic Vixzen icons")
        return
    if not os.path.isdir(BACKUP):
        shutil.copytree(THEME, BACKUP, symlinks=True)
        print("backup at assets/icons/Vixzen-classic/")
    changed, files = 0, 0
    for root, _dirs, names in os.walk(THEME):
        for name in names:
            if not name.endswith(".svg"):
                continue
            p = os.path.join(root, name)
            if os.path.islink(p):
                continue
            txt = open(p).read()
            for old, new in NEON.items():
                for variant in (old, old.lower(), old.upper()):
                    if variant in txt:
                        changed += txt.count(variant)
                        txt = txt.replace(variant, new)
            open(p, "w").write(txt)
            files += 1
    print(f"neon recolor: {changed} fills across {files} files")


if __name__ == "__main__":
    main()
