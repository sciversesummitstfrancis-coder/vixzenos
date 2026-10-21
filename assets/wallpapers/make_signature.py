#!/usr/bin/env python3
"""VixzenOS signature wallpaper — 1920x1080 PNG with logo + name + tagline.
Offline, Pillow only. Output: assets/wallpapers/vixzen-signature-1920x1080.png
Use today: gsettings set org.gnome.desktop.background picture-uri-dark
  file:///home/<user>/vixzenos/assets/wallpapers/vixzen-signature-1920x1080.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def font(size, bold=False):
    for p in ("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
              "/usr/share/fonts/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

img = Image.new("RGB", (W, H))
px = img.load()
top, bot = (79, 70, 229), (2, 6, 23)
for y in range(H):
    c = lerp(top, bot, y / H)
    for x in range(0, W, 2):
        px[x, y] = c
        px[x + 1, y] = c
d = ImageDraw.Draw(img, "RGBA")
d.ellipse([1330, 60, 1730, 460], fill=(34, 211, 238, 38))
d.ellipse([180, 630, 720, 1170], fill=(124, 124, 255, 34))
d.ellipse([-140, -140, 300, 300], fill=(255, 255, 255, 14))

# Logo badge (rounded square + V + dot), centered upper-middle
S, lx, ly = 220, (W - 220) // 2, 250
d.rounded_rectangle([lx, ly, lx + S, ly + S], radius=48, fill=(20, 18, 60, 255),
                    outline=(124, 124, 255, 255), width=4)
d.line([(lx + 52, ly + 62), (lx + 110, ly + 158), (lx + 168, ly + 62)],
       fill="white", width=22, joint="curve")
d.ellipse([lx + 100, ly + 52, lx + 120, ly + 72], fill=(34, 211, 238, 255))

d.text((W // 2, 560), "VixzenOS", font=font(120, True), fill="white", anchor="mm")
d.text((W // 2, 650), "Lightweight  •  Graphical  •  Yours", font=font(40),
       fill=(205, 205, 225), anchor="mm")
out = os.path.join(HERE, "vixzen-signature-1920x1080.png")
img.save(out)
print("wrote", out, img.size, os.path.getsize(out) // 1024, "KB")
