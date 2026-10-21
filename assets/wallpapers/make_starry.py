#!/usr/bin/env python3
"""Starry-night Vixzen wallpaper — 1920x1080 PNG, Pillow only, no downloads.
Deep-space navy gradient + layered stars + indigo/teal nebula glows.
Output: assets/wallpapers/vixzen-starry-1920x1080.png
"""
import os, random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080
random.seed(20260924)

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

img = Image.new("RGB", (W, H))
px = img.load()
top, bot = (8, 12, 38), (2, 4, 14)
for y in range(H):
    c = lerp(top, bot, y / H)
    for x in range(0, W, 2):
        px[x, y] = c
        px[x + 1, y] = c

d = ImageDraw.Draw(img, "RGBA")
# Nebula glows (soft concentric ellipses)
for cx, cy, rx, ry, col in [
        (1350, 320, 420, 260, (79, 70, 229)),
        (420, 760, 480, 300, (6, 182, 214)),
        (960, 540, 700, 420, (30, 27, 75))]:
    for i in range(6, 0, -1):
        a = 10 + (6 - i) * 4
        d.ellipse([cx - rx * i // 6, cy - ry * i // 6,
                   cx + rx * i // 6, cy + ry * i // 6],
                  fill=col + (a,))
# Stars: far (tiny dim) + near (bright, some with cross sparkle)
for _ in range(420):
    x, y = random.randrange(W), random.randrange(H)
    b = random.randrange(90, 170)
    img.putpixel((x, y), (b, b, min(255, b + 30)))
for _ in range(90):
    x, y = random.randrange(W), random.randrange(H)
    r = random.choice([1, 1, 2])
    b = random.randrange(200, 256)
    tint = random.choice([(255, 255, 255), (200, 220, 255), (255, 240, 220)])
    col = tuple(min(255, b if i == 0 else int(b * 0.95)) if False else v for i, v in enumerate(tint))
    d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    if r == 2 and random.random() < 0.4:
        d.line([x - 5, y, x + 5, y], fill=col + (120,))
        d.line([x, y - 5, x, y + 5], fill=col + (120,))

out = os.path.join(HERE, "vixzen-starry-1920x1080.png")
img.save(out)
print("wrote", out, img.size, os.path.getsize(out) // 1024, "KB")
