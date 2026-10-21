#!/usr/bin/env python3
"""Generate VixzenOS boot artwork (GRUB background + logo) with Pillow.
No downloads, no heavy deps. Output: assets/boot/background.png (1280x720),
assets/boot/logo.png (256px, transparent). Run once; PNGs are committed.
"""
import os
import math
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def background():
    w, h = 1280, 720
    top, bot = (79, 70, 229), (2, 6, 23)  # indigo -> near-black
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        c = lerp(top, bot, y / h)
        for x in range(w):
            px[x, y] = c
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse([880, 40, 1140, 300], fill=(34, 211, 238, 40))
    d.ellipse([120, 420, 480, 780], fill=(124, 124, 255, 36))
    d.text((60, 600), "VixzenOS", fill=(255, 255, 255, 230))
    d.text((62, 640), "Lightweight  -  Graphical  -  Yours", fill=(200, 200, 220, 200))
    img.save(os.path.join(HERE, "background.png"))
    print("wrote background.png", img.size)

def logo():
    s = 256
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([16, 16, s - 16, s - 16], radius=52, fill=(79, 70, 229, 255))
    d.line([(68, 80), (128, 184), (188, 80)], fill="white", width=24, joint="curve")
    d.ellipse([116, 68, 140, 92], fill=(34, 211, 238, 255))
    img.save(os.path.join(HERE, "logo.png"))
    print("wrote logo.png", img.size)

def frames():
    """Comet boot frames (archived look). Superseded by minimal_frames()
    per the restrained boot spec. Regenerate with frames(); video frames
    live in assets/boot/frames-video/.
    Same filenames/count/size as stock spinner (36 animation + 30 throbber,
    32x32 RGBA) so the theme mechanics are unchanged — only the look is ours:
    an indigo comet with a cyan glow trail (progress) + a pulsing Vixzen ring
    (throbber). Output: assets/boot/frames/.
    """
    out = os.path.join(HERE, "frames")
    os.makedirs(out, exist_ok=True)
    s = 32
    cx = cy = 16
    for i in range(36):
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        ang = (i / 36) * 2 * math.pi
        for k in range(6):  # glow trail behind the head
            a = ang - k * 0.22
            x = cx + 10 * math.cos(a)
            y = cy + 10 * math.sin(a)
            r = 5 - k * 0.7
            alpha = int(150 - k * 24)
            d.ellipse([x - r, y - r, x + r, y + r],
                      fill=(34, 211, 238, max(alpha, 0)))
        hx = cx + 10 * math.cos(ang)
        hy = cy + 10 * math.sin(ang)
        d.ellipse([hx - 3.4, hy - 3.4, hx + 3.4, hy + 3.4],
                  fill=(124, 124, 255, 255))
        d.ellipse([hx - 1.6, hy - 1.6, hx + 1.6, hy + 1.6],
                  fill=(255, 255, 255, 255))
        img.save(os.path.join(out, f"animation-{i + 1:04d}.png"))
    for i in range(30):
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        t = i / 30
        r = 6 + 6 * t
        alpha = int(220 * (1 - t))
        w = 3 if t < 0.5 else 2
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=(79, 70, 229, alpha), width=w)
        d.ellipse([cx - 3, cy - 3, cx + 3, cy + 3],
                  fill=(34, 211, 238, 255))
        img.save(os.path.join(out, f"throbber-{i + 1:04d}.png"))
    print(f"wrote 66 frames to {out}")




def minimal_frames():
    """Restrained boot animation (the spec look): a thin ring that gently
    breathes in opacity and diameter — no trails, no spin, no flash.
    24 animation + 20 throbber frames, 48x48 RGBA, same filenames two-step
    expects. Output: assets/boot/frames/.
    """
    out = os.path.join(HERE, "frames")
    os.makedirs(out, exist_ok=True)
    # clear any previous (busier) frames so counts are exact
    for old in list(os.listdir(out)):
        if old.startswith(("animation-", "throbber-")):
            os.remove(os.path.join(out, old))
    s = 48
    cx = cy = 24
    for i in range(24):
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        t = i / 24
        r = 13 + 2.5 * math.sin(2 * math.pi * t)
        alpha = int(150 + 70 * math.sin(2 * math.pi * t))
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  outline=(200, 200, 235, max(alpha, 0)), width=2)
        img.save(os.path.join(out, f"animation-{i + 1:04d}.png"))
    for i in range(20):
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        t = i / 20
        alpha = int(120 + 80 * math.sin(2 * math.pi * t))
        d.ellipse([cx - 8, cy - 8, cx + 8, cy + 8],
                  outline=(200, 200, 235, max(alpha, 0)), width=2)
        img.save(os.path.join(out, f"throbber-{i + 1:04d}.png"))
    print(f"wrote 44 minimal frames to {out}")


def grub_background():
    """Clean boot-menu backdrop (spec: completely dark, logo centered,
    no text, no glow). Overwrites assets/boot/background.png (GRUB only)."""
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), (2, 4, 14))
    d = ImageDraw.Draw(img, "RGBA")
    mark = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
    mark = mark.resize((150, 150), Image.LANCZOS)
    dim = Image.new("RGBA", mark.size, (0, 0, 0, 0))
    dim = Image.blend(Image.new("RGBA", mark.size, (0, 0, 0, 0)), mark, 0.85)
    img.paste(dim, (w // 2 - 75, 120), dim)
    d.text((w // 2 - 52, 300), "VixzenOS", fill=(150, 150, 170, 255))
    img.save(os.path.join(HERE, "background.png"))
    print("wrote background.png (clean)", img.size)

if __name__ == "__main__":
    grub_background()
    logo()
    minimal_frames()
