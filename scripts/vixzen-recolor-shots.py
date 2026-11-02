#!/usr/bin/env python3
"""Recolor legacy accents in the website screenshots to Vixzen Blue.

The three `website/assets/shot-*.png` files were captured once, before the blue
rebrand, so they still carry the old indigo (#4F46E5 / #7C7CFF) and neon-green
(#00E676) accents. Re-capturing needs a live GNOME session, which the build box
does not have, so this does a targeted hue remap instead.

Matching is deliberately narrow — hue band, channel dominance, saturation and a
brightness floor — because dark navy wallpapers are also "saturated blue" and a
plain hue filter drags the whole background with it:

  * old indigo: blue-dominant, red and green nearly equal, hue 228-268
  * old neon green: green-dominant, hue 122-172
  * target: Vixzen Blue hue (217), saturation capped at the brand value,
    brightness preserved so glows stay glows

Only the matched pixels' hue and saturation change; value is untouched, so the
lighting of the screenshot is preserved.

Usage:
    python3 scripts/vixzen-recolor-shots.py            # rewrite in place
    python3 scripts/vixzen-recolor-shots.py --check    # report only, exit 1 if legacy accents remain
"""
import colorsys
import pathlib
import sys

from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[1]
SHOTS = sorted((REPO / "website" / "assets").glob("shot-*.png"))

TARGET_HUE = 217 / 360
TARGET_SAT = 0.85
MIN_SAT = 0.35
MIN_VAL = 0.28


def is_legacy(r, g, b):
    """True when a pixel carries one of the pre-blue accents."""
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < MIN_SAT or v < MIN_VAL:
        return False
    deg = h * 360
    indigo = 228 <= deg <= 268 and abs(r - g) <= 26 and b >= g + 40
    neon = 122 <= deg <= 172 and g >= r + 40 and g >= b + 20
    return indigo or neon


def remap(r, g, b):
    _h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    nr, ng, nb = colorsys.hsv_to_rgb(TARGET_HUE, min(s, TARGET_SAT), v)
    return round(nr * 255), round(ng * 255), round(nb * 255)


def _pixels(im):
    """Iterate RGB triples without the deprecated Image.getdata()."""
    data = im.tobytes()
    for i in range(0, len(data), 3):
        yield data[i], data[i + 1], data[i + 2]


def recolor(im):
    px = im.load()
    w, h = im.size
    changed = 0
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if is_legacy(r, g, b):
                px[x, y] = remap(r, g, b)
                changed += 1
    return changed


def main():
    check = "--check" in sys.argv
    if not SHOTS:
        print("no website screenshots found", file=sys.stderr)
        return 1
    failed = False
    for path in SHOTS:
        im = Image.open(path).convert("RGB")
        before = sum(is_legacy(*p) for p in _pixels(im))
        if check:
            print(f"{path.name}: {before} legacy-accent pixels")
            failed = failed or before > 0
            continue
        changed = recolor(im)
        im.save(path, optimize=True)
        after = sum(is_legacy(*p) for p in _pixels(im))
        print(f"{path.name}: recolored {changed} px (was {before}, {after} left)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
