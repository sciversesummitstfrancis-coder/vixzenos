#!/usr/bin/env python3
"""Build the VixzenHand glove pointer from ~/Downloads/Cursor.jpg.

White background -> transparent (border flood-fill, interior kept opaque),
resized to 32px, hotspot on the middle-fingertip, written as a real Xcursor
file (no xcursorgen needed). Output: assets/cursors/VixzenHand/.

Run: python3 assets/cursors/make_hand_cursor.py [source.jpg]
"""
import os
import struct
import sys
from collections import deque

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE = 32


def load_rgba(src):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    px = im.load()
    # Barrier fill: traversable = anything not black-outline (lets white AND
    # gray JPEG edges through, stops at the dark outline). Bottom rows are
    # sealed as a wall (open cuffs must not leak the fill inside).
    SEAL = 3
    dark = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if min(r, g, b) < 90:
                dark[y * w + x] = 1
    seen = bytearray(w * h)
    dq = deque()
    for x in range(w):
        dq.append((x, 0))
        dq.append((x, h - 1))
    for y in range(h):
        dq.append((0, y))
        dq.append((w - 1, y))
    while dq:
        x, y = dq.popleft()
        if not (0 <= x < w and 0 <= y < h - SEAL):
            continue
        i = y * w + x
        if seen[i] or dark[i]:
            continue
        seen[i] = 1
        dq.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    opx = out.load()
    for y in range(h):
        for x in range(w):
            if seen[y * w + x]:
                continue  # background -> transparent
            opx[x, y] = px[x, y] + (255,)
    return out


def fingertip(im):
    """Hotspot: the index fingertip (leftmost tall finger), not the mean
    of all fingertips. Topmost dark row -> mean x of dark pixels in the
    rows just below it."""
    w, h = im.size
    px = im.load()
    top = None
    for y in range(int(h * 0.25)):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 128 and min(r, g, b) < 90:
                top = y
                break
        if top is not None:
            break
    if top is None:
        return w // 3, 2
    xs = []
    for y in range(top, min(top + int(h * 0.06) + 1, h)):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 128 and min(r, g, b) < 90:
                xs.append(x)
    # leftmost cluster = index finger
    xs.sort()
    cluster = [xs[0]]
    for x in xs[1:]:
        if x - cluster[-1] > max(w // 20, 2):
            break
        cluster.append(x)
    return sum(cluster) // len(cluster), max(top, 0)


def write_xcursor(path, img, xhot, yhot, size=SIZE):
    """Write one image. Layout matches real-world files byte-for-byte:
    file header, TOC, then per image [36, type, subtype, version, w, h,
    xhot, yhot, delay] + ARGB pixels. (The leading 36 is what every
    shipping cursor file carries; our first attempt omitted the chunk
    header fields and rendered as a box.)"""
    return write_xcursor_multi(path, [(img, xhot, yhot, size)])


def write_xcursor_multi(path, images):
    """images: list of (PIL image, xhot, yhot, nominal_size)."""
    ntoc = len(images)
    chunks = []
    for img, xhot, yhot, nominal in images:
        w, h = img.size
        px = img.load()
        blob = struct.pack("<IIIIIIIII", 36, 0xFFFD0002, nominal, 1,
                           w, h, xhot, yhot, 0)
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                blob += struct.pack("<I", (a << 24) | (r << 16) | (g << 8) | b)
        chunks.append((nominal, blob))
    pos = 16 + 12 * ntoc
    out = struct.pack("<IIII", 0x72756358, 16, 0x10000, ntoc)
    for nominal, blob in chunks:
        out += struct.pack("<III", 0xFFFD0002, nominal, pos)
        pos += len(blob)
    for _, blob in chunks:
        out += blob
    with open(path, "wb") as f:
        f.write(out)


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
        "~/Downloads/Cursor.jpg")
    rgba = load_rgba(src)
    # Hotspot FIRST on the full image (index fingertip; fractions are
    # crop-invariant), then tight crop for the artwork.
    hx, hy = fingertip(rgba)
    hfx, hfy = hx / rgba.size[0], hy / rgba.size[1]
    bbox = rgba.getbbox()
    m = 8
    rgba = rgba.crop((max(bbox[0] - m, 0), max(bbox[1] - m, 0),
                      bbox[2] + m, bbox[3] + m))
    # three sizes like shipping themes (nominal 24/32/48)
    multi = []
    for px, nom in ((32, 24), (48, 32), (64, 48)):
        small = rgba.resize((px, px), Image.LANCZOS)
        multi.append((small, int(hfx * px), int(hfy * px), nom))
    theme = os.path.join(HERE, "VixzenHand", "cursors")
    os.makedirs(theme, exist_ok=True)
    write_xcursor_multi(os.path.join(theme, "left_ptr"), multi)
    for alias in ("default", "arrow", "top_left_arrow", "left-arrow"):
        p = os.path.join(theme, alias)
        try:
            if os.path.islink(p) or os.path.exists(p):
                os.remove(p)
            os.symlink("left_ptr", p)
        except OSError:
            pass
    idx = os.path.join(HERE, "VixzenHand", "index.theme")
    if not os.path.isfile(idx):
        with open(idx, "w") as f:
            f.write("[Icon Theme]\nName=VixzenHand\nComment=Vixzen glove "
                    "pointer (main arrow); falls back to McMojave\n"
                    "Inherits=McMojave\n")
    print(f"VixzenHand pointer: 32/48/64px, hotspot=({hx},{hy}) "
          f"-> fractions ({hfx:.3f},{hfy:.3f})")


if __name__ == "__main__":
    main()
