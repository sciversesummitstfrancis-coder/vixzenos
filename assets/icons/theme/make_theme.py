#!/usr/bin/env python3
"""Generate the Vixzen icon theme (offline, no downloads).
Indigo folders + trash + home in Vixzen style; everything else inherits
Adwaita, so the theme is tiny and safe. Output: assets/icons/theme/Vixzen/
"""
import os

HERE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Vixzen")
PLACES = os.path.join(HERE, "scalable", "places")
os.makedirs(PLACES, exist_ok=True)

INDIGO_D = "#3730A3"
INDIGO = "#4F46E5"
INDIGO_L = "#7C7CFF"
DARK = "#23263A"

FOLDER = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#6BB6FF"/><stop offset="1" stop-color="#1E6FEB"/>
</linearGradient></defs>
<path d="M4 12 Q4 8 8 8 H18 L22 12 H40 Q44 12 44 16 V20 H4 Z" fill="#174A9E"/>
<rect x="4" y="18" width="40" height="20" rx="4" fill="url(#f)"/>
<rect x="4" y="18" width="40" height="4" fill="#FFFFFF" opacity="0.45"/>
</svg>
"""

FOLDER_OPEN = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#6BB6FF"/><stop offset="1" stop-color="#1E6FEB"/>
</linearGradient></defs>
<path d="M4 12 Q4 8 8 8 H18 L22 12 H40 Q44 12 44 16 V20 H4 Z" fill="#174A9E"/>
<path d="M6 22 L14 34 H42 L34 22 Z" fill="#FFE08A"/>
<rect x="4" y="30" width="40" height="8" rx="4" fill="url(#f)"/>
</svg>
"""

TRASH = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<path d="M14 14 H34 M19 14 V10 H29 V14 M17 14 L19 40 H29 L31 14" fill="none" stroke="#E8EAF2" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
<path d="M22 20 V34 M26 20 V34" stroke="#22D3EE" stroke-width="3" stroke-linecap="round"/>
</svg>
"""

HOME = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<path d="M8 24 L24 10 L40 24" fill="none" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
<rect x="15" y="24" width="18" height="14" rx="2" fill="#4F46E5"/>
<rect x="21" y="30" width="6" height="8" fill="#FFD93D"/>
</svg>
"""

FILES = {"folder.svg": FOLDER, "folder-open.svg": FOLDER_OPEN,
         "user-trash.svg": TRASH, "user-home.svg": HOME}
for name, svg in FILES.items():
    with open(os.path.join(PLACES, name), "w") as f:
        f.write(svg)
    print("wrote", name)
# Folder flavors all share the Vixzen folder look.
for link in ("folder-download.svg", "folder-documents.svg", "folder-music.svg",
             "folder-pictures.svg", "folder-videos.svg", "folder-remote.svg",
             "trash-full.svg"):
    p = os.path.join(PLACES, link)
    try:
        if os.path.islink(p) or os.path.exists(p):
            os.remove(p)
        target = "user-trash.svg" if "trash" in link else "folder.svg"
        os.symlink(target, p)
        print("linked", link, "->", target)
    except Exception as e:
        print("link skip", link, e)

INDEX = """[Icon Theme]
Name=Vixzen
Comment=VixzenOS icon theme — Vixzen brand folders + core apps over Adwaita
Inherits=Adwaita
Directories=scalable/places,scalable/apps

[scalable/places]
Size=48
Type=Scalable
MinSize=8
MaxSize=512
Context=Places

[scalable/apps]
Size=48
Type=Scalable
MinSize=8
MaxSize=512
Context=Applications
"""
with open(os.path.join(HERE, "index.theme"), "w") as f:
    f.write(INDEX)
print("wrote index.theme")

# ---- Core app icons: BRIGHT per-app plates (readable at a glance,
# high contrast for older eyes). Original art, nothing copied. ----
APPS = os.path.join(HERE, "scalable", "apps")
os.makedirs(APPS, exist_ok=True)

def plate(c1, c2, inner, border="#FFFFFF"):
    return ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
            f"<defs><linearGradient id='p' x1='0' y1='0' x2='0' y2='1'>"
            f"<stop offset='0' stop-color='{c1}'/><stop offset='1' stop-color='{c2}'/>"
            "</linearGradient></defs>"
            "<rect x='2' y='2' width='44' height='44' rx='12' fill='url(#p)'/>"
            f"<rect x='2.5' y='2.5' width='43' height='43' rx='11.5' fill='none' "
            f"stroke='{border}' stroke-opacity='0.55'/>" + inner + "</svg>")

teeth = "".join(
    "<rect x='21.5' y='7' width='5' height='8' rx='2' fill='#FFFFFF' "
    f"transform='rotate({d} 24 24)'/>" for d in range(0, 360, 45))
dots = "".join(
    f"<circle cx='{x}' cy='{y}' r='2.6' fill='#FFD93D'/>"
    for x in (16, 24, 32) for y in (25, 32, 39))

APP_ART = {
    # (plate_top, plate_bottom, glyph_svg)
    "files": ("#6BB6FF", "#1E6FEB",
              "<path d='M10 18 Q10 15 13 15 H21 L23 17 H36 Q39 17 39 20 V22 H10 Z' fill='#0B3D91'/>"
              "<rect x='10' y='21' width='29' height='13' rx='3' fill='white' opacity='0.92'/>"),
    "terminal": ("#2B2F3A", "#101218",
                 "<path d='M15 19 L22 24 L15 29' fill='none' stroke='#00E676' stroke-width='3.4' "
                 "stroke-linecap='round' stroke-linejoin='round'/>"
                 "<path d='M25 30 H34' stroke='white' stroke-width='3.2' stroke-linecap='round'/>"),
    "settings": ("#8B8FA3", "#4A4E69",
                 teeth + "<circle cx='24' cy='24' r='7.5' fill='white'/>"
                 "<circle cx='24' cy='24' r='3' fill='#4F46E5'/>"),
    "software": ("#FF9A3D", "#E8590C",
                 "<rect x='13' y='18' width='22' height='17' rx='3' fill='none' stroke='white' stroke-width='3.4'/>"
                 "<path d='M18 18 v-3 a6 6 0 0 1 12 0 v3' fill='none' stroke='white' stroke-width='3'/>"
                 "<circle cx='24' cy='26' r='3.4' fill='white'/>"),
    "calculator": ("#3B3F4E", "#171923",
                   "<rect x='17' y='12' width='14' height='6' rx='1.5' fill='#7CFFB2'/>" + dots),
    "calendar": ("#FFFFFF", "#DCE3F0",
                 "<rect x='11' y='13' width='26' height='7' rx='2' fill='#F43F5E'/>"
                 "<rect x='11' y='20' width='26' height='18' rx='2' fill='none' stroke='#334155' stroke-width='2.6'/>"
                 "<path d='M18 9 V15 M30 9 V15' stroke='#4F46E5' stroke-width='3.4' stroke-linecap='round'/>"
                 "<circle cx='24' cy='29' r='3.4' fill='#4F46E5'/>"),
    "editor": ("#FFFFFF", "#C9D6F2",
               "<path d='M17 14 H29 M17 20 H29 M17 26 H25' stroke='#1E293B' stroke-width='2.6'/>"
               "<path d='M28 33 L37 24 L40 27 L31 36 L27 37 Z' fill='#4F46E5'/>"),
}
for key, (c1, c2, inner) in APP_ART.items():
    with open(os.path.join(APPS, f"vixzen-{key}.svg"), "w") as f:
        f.write(plate(c1, c2, inner))
    print("wrote vixzen-" + key + ".svg")

# Point theme names at our art (brand + common fallbacks).
MAPPINGS = {
    "org.gnome.Nautilus.svg": "vixzen-files.svg",
    "org.gnome.Ptyxis.svg": "vixzen-terminal.svg",
    "org.gnome.Console.svg": "vixzen-terminal.svg",
    "org.gnome.Terminal.svg": "vixzen-terminal.svg",
    "utilities-terminal.svg": "vixzen-terminal.svg",
    "org.gnome.Settings.svg": "vixzen-settings.svg",
    "org.gnome.Software.svg": "vixzen-software.svg",
    "org.gnome.Calculator.svg": "vixzen-calculator.svg",
    "accessories-calculator.svg": "vixzen-calculator.svg",
    "org.gnome.Calendar.svg": "vixzen-calendar.svg",
    "org.gnome.TextEditor.svg": "vixzen-editor.svg",
    "accessories-text-editor.svg": "vixzen-editor.svg",
}
for link, target in MAPPINGS.items():
    p = os.path.join(APPS, link)
    try:
        if os.path.islink(p) or os.path.exists(p):
            os.remove(p)
        os.symlink(target, p)
    except Exception as e:
        print("link skip", link, e)
print("app mappings done:", len(MAPPINGS))
