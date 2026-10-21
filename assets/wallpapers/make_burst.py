#!/usr/bin/env python3
"""Vixzen burst wallpaper — dark base with a neon green/cyan energy burst
radiating from center-right (the CachyOS-style vibe, Vixzen-owned).
Output: assets/wallpapers/vixzen-burst-1920x1080.png. Run once; committed.
"""
import os
import math
import random
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def burst():
    random.seed(42)
    base = Image.new("RGB", (W, H), (2, 8, 6))
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    cx, cy = 1150, 540
    greens = [(0, 230, 118), (34, 211, 238), (0, 180, 120), (120, 255, 190)]
    for _ in range(750):
        ang = random.uniform(0, 2 * math.pi)
        r0 = random.uniform(20, 120)
        length = random.uniform(120, 720)
        wdt = random.choice((1, 1, 2, 2, 3))
        col = random.choice(greens)
        alpha = random.randint(40, 170)
        x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)
        x1, y1 = cx + (r0 + length) * math.cos(ang), cy + (r0 + length) * math.sin(ang)
        d.line([(x0, y0), (x1, y1)], fill=col + (alpha,), width=wdt)
    # hot core glow
    for r, a in ((150, 26), (100, 40), (55, 70)):
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow, "RGBA")
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, 230, 150, a))
        layer = Image.alpha_composite(layer, glow)
    out = Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")
    out.save(os.path.join(HERE, "vixzen-burst-1920x1080.png"))
    print("wrote vixzen-burst-1920x1080.png", out.size)


if __name__ == "__main__":
    burst()
