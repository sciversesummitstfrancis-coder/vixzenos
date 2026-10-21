#!/usr/bin/env python3
"""Vixzen icon set part 2 — original designs closing every stock leak.

Same language as part 1 (48px squircle, gradient tile, white inner stroke,
white glyph): 8 app icons + 7 mimetypes. Nothing copied from any OS.
Run: python3 assets/icons/theme/make_vixzen_icons.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.join(HERE, "Vixzen", "scalable", "apps")
MIME = os.path.join(HERE, "Vixzen", "scalable", "mimetypes")


def tile(c1, c2, gid="g"):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
            f"<defs><linearGradient id='{gid}' x1='0' y1='0' x2='1' y2='1'>"
            f"<stop offset='0' stop-color='{c1}'/>"
            f"<stop offset='1' stop-color='{c2}'/></linearGradient></defs>"
            f"<rect x='2' y='2' width='44' height='44' rx='12' fill='url(#{gid})'/>"
            f"<rect x='2.5' y='2.5' width='43' height='43' rx='11.5' fill='none' "
            f"stroke='#FFFFFF' stroke-opacity='0.55'/>")


def save(path, body):
    with open(path, "w") as f:
        f.write(body + "</svg>\n")


def app(name, c1, c2, glyph, links=()):
    save(os.path.join(APPS, name), tile(c1, c2) + glyph)
    for link in links:
        p = os.path.join(APPS, link)
        if os.path.islink(p) or os.path.exists(p):
            os.remove(p)
        os.symlink(name, p)


def doc(name, band, glyph):
    body = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
            f"<path d='M12 4 H30 L38 12 V44 H12 Z' fill='#FFFFFF'/>"
            f"<path d='M30 4 L38 12 H30 Z' fill='#D4D8E3'/>"
            f"<rect x='12' y='34' width='26' height='10' fill='{band}'/>"
            f"{glyph}")
    save(os.path.join(MIME, name), body)


def main():
    os.makedirs(APPS, exist_ok=True)
    os.makedirs(MIME, exist_ok=True)
    W = "stroke='#FFFFFF' stroke-width='2.6' fill='none' opacity='0.95'"
    F = "fill='#FFFFFF' opacity='0.95'"
    # -- apps: white glyph on brand gradients --
    app("vixzen-chrome.svg", "#4F46E5", "#06B6D4",
        "<path d='M24 13 A11 11 0 0 1 33.5 29.5' stroke='#FB7185' stroke-width='4' fill='none'/>"
        "<path d='M33.5 29.5 A11 11 0 0 1 14.5 29.5' stroke='#FBBF24' stroke-width='4' fill='none'/>"
        "<path d='M14.5 29.5 A11 11 0 0 1 24 13' stroke='#34D399' stroke-width='4' fill='none'/>"
        "<circle cx='24' cy='24' r='5.5' fill='#FFFFFF'/>"
        "<circle cx='24' cy='24' r='2.6' fill='#06B6D4'/>",
        links=("com.google.Chrome.svg", "google-chrome.svg"))
    app("vixzen-loupe.svg", "#0891B2", "#22D3EE",
        f"<rect x='13' y='14' width='22' height='16' rx='2' {W}/>"
        f"<path d='M13 20 L20 26 L25 21 L29 25 L35 19 V14 H13 Z' fill='#FFFFFF' opacity='0.9'/>"
        f"<circle cx='30' cy='18.5' r='1.8' fill='#0891B2'/>",
        links=("org.gnome.Loupe.svg",))
    app("vixzen-snapshot.svg", "#6D28D9", "#A78BFA",
        f"<rect x='12' y='16' width='24' height='17' rx='4' {W}/>"
        f"<circle cx='24' cy='24.5' r='5' {W}/>"
        f"<rect x='19' y='12.5' width='10' height='4' rx='2' {F}/>",
        links=("org.gnome.Snapshot.svg",))
    app("vixzen-decibels.svg", "#4F46E5", "#7C7CFF",
        "".join(f"<rect x='{15 + i * 5}' y='{24 - h}' width='3' height='{2 * h}' rx='1.5' {F}/>"
                for i, h in enumerate((4, 8, 5, 10, 6))),
        links=("org.gnome.Decibels.svg",))
    app("vixzen-extensions.svg", "#0E7490", "#22D3EE",
        f"<path d='M20 12 h5 v5 h5 v5 h-5 v5 h-5 v-5 h-5 v-5 h5 Z' {F}/>"
        f"<circle cx='31' cy='31' r='6' {W}/>",
        links=("com.mattjakeman.ExtensionManager.svg",))
    app("vixzen-disks.svg", "#334155", "#64748B",
        f"<circle cx='24' cy='24' r='11' {W}/>"
        f"<path d='M24 24 L24 13 A11 11 0 0 1 35 24 Z' fill='#FFFFFF' opacity='0.9'/>",
        links=("org.gnome.baobab.svg",))
    app("vixzen-contacts.svg", "#1D4ED8", "#60A5FA",
        f"<circle cx='24' cy='19' r='6' {F}/>"
        f"<path d='M13 36 Q13 28 24 28 Q35 28 35 36' {W}/>",
        links=("org.gnome.Contacts.svg",))
    app("vixzen-maps.svg", "#15803D", "#4ADE80",
        f"<path d='M24 10 Q31 10 31 18 Q31 28 24 34 Q17 28 17 18 Q17 10 24 10' {W}/>"
        f"<circle cx='24' cy='18' r='3' {F}/>",
        links=("org.gnome.Maps.svg",))
    # -- mimetypes: white page, color band, glyph --
    doc("text-x-generic.svg", "#4F46E5",
        "".join(f"<rect x='16' y='{16 + i * 4}' width='{16 if i < 2 else 10}' height='2' fill='#4F46E5'/>" for i in range(3)))
    doc("image-x-generic.svg", "#0891B2",
        "<path d='M16 28 L22 21 L26 25 L30 20 L34 24 V30 H16 Z' fill='#0891B2'/>")
    doc("video-x-generic.svg", "#6D28D9",
        "<path d='M21 18 L31 24 L21 30 Z' fill='#6D28D9'/>")
    doc("audio-x-generic.svg", "#EA580C",
        "<rect x='19' y='16' width='3' height='12' rx='1.5' fill='#EA580C'/>"
        "<rect x='26' y='16' width='3' height='12' rx='1.5' fill='#EA580C'/>")
    doc("application-pdf.svg", "#DC2626",
        "<rect x='16' y='16' width='16' height='12' rx='2' fill='#DC2626'/>")
    doc("package-x-generic.svg", "#B45309",
        "<rect x='17' y='20' width='14' height='10' rx='1.5' fill='none' stroke='#B45309' stroke-width='2'/>"
        "<line x1='17' y1='24' x2='31' y2='24' stroke='#B45309' stroke-width='2'/>")
    doc("application-x-executable.svg", "#16A34A",
        "<path d='M18 20 L26 24 L18 28' stroke='#16A34A' stroke-width='2.5' fill='none'/>")
    print("15 Vixzen icons written (8 apps + 7 mimetypes)")


if __name__ == "__main__":
    main()
