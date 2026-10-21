#!/usr/bin/env python3
"""Vixzen icon set part 3 — close every remaining stock leak.

Neon tile (matches the recolored set): #00E676 -> #00A651 diagonal,
white inner stroke, white glyphs. Filenames = exact Icon= names from
installed .desktop files; symlinks for aliases.
Run: python3 assets/icons/theme/make_vixzen_icons3.py
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.join(HERE, "Vixzen", "scalable", "apps")
MIME = os.path.join(HERE, "Vixzen", "scalable", "mimetypes")

TILE = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
        "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
        "<stop offset='0' stop-color='#00E676'/>"
        "<stop offset='1' stop-color='#00A651'/></linearGradient></defs>"
        "<rect x='2' y='2' width='44' height='44' rx='12' fill='url(#g)'/>"
        "<rect x='2.5' y='2.5' width='43' height='43' rx='11.5' fill='none' "
        "stroke='#FFFFFF' stroke-opacity='0.55'/>")


def save(path, body):
    with open(path, "w") as f:
        f.write(body + "</svg>\n")


def app(name, glyph, links=()):
    save(os.path.join(APPS, name), TILE + glyph)
    for link in links:
        p = os.path.join(APPS, link)
        if os.path.islink(p) or os.path.exists(p):
            os.remove(p)
        os.symlink(name, p)


def main():
    os.makedirs(APPS, exist_ok=True)
    W = "stroke='#FFFFFF' stroke-width='2.6' fill='none' opacity='0.95'"
    F = "fill='#FFFFFF' opacity='0.95'"
    # media
    app("vixzen-mpv.svg",
        "<path d='M20 16 L32 24 L20 32 Z' fill='#FFFFFF' opacity='0.95'/>",
        links=("mpv.svg",))
    app("vixzen-showtime.svg",
        "<rect x='13' y='14' width='22' height='16' rx='3' " + W + "/>"
        "<path d='M22 18 L28 22 L22 26 Z' fill='#FFFFFF' opacity='0.95'/>",
        links=("org.gnome.Showtime.svg",))
    app("vixzen-rygel.svg",
        "<circle cx='24' cy='24' r='4' fill='#FFFFFF' opacity='0.95'/>"
        "<path d='M24 12 A12 12 0 0 1 36 24' " + W + "/>"
        "<path d='M24 36 A12 12 0 0 1 12 24' " + W + "/>",
        links=("rygel.svg",))
    # 3d / gamedev
    app("vixzen-blender.svg",
        "<path d='M24 10 L36 30 L12 30 Z' " + W + "/>"
        "<circle cx='24' cy='25' r='2.5' fill='#FFFFFF' opacity='0.95'/>",
        links=("blender.svg",))
    app("vixzen-godot.svg",
        f"<rect x='15' y='14' width='18' height='14' rx='3' {W}/>"
        f"<circle cx='21' cy='20' r='1.6' fill='#04120A'/>"
        f"<circle cx='27' cy='20' r='1.6' fill='#04120A'/>"
        f"<rect x='19' y='29' width='10' height='6' rx='2' {F}/>",
        links=("godot.svg",))
    # office
    app("vixzen-writer.svg",
        "<path d='M15 6 H27 L33 12 V42 H15 Z' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='18' y='20' width='12' height='2' fill='#00A651'/>"
        "<rect x='18' y='25' width='12' height='2' fill='#00A651'/>"
        "<rect x='18' y='30' width='8' height='2' fill='#00A651'/>",
        links=("libreoffice-writer.svg",))
    app("vixzen-calc.svg",
        "<rect x='15' y='8' width='18' height='32' rx='3' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='18' y='12' width='12' height='6' rx='1' fill='#00A651'/>"
        "<circle cx='21' cy='25' r='1.6' fill='#00A651'/><circle cx='27' cy='25' r='1.6' fill='#00A651'/>"
        "<circle cx='21' cy='31' r='1.6' fill='#00A651'/><circle cx='27' cy='31' r='1.6' fill='#00A651'/>",
        links=("libreoffice-calc.svg",))
    app("vixzen-impress.svg",
        "<rect x='12' y='12' width='24' height='18' rx='2' fill='#FFFFFF' opacity='0.95'/>"
        "<path d='M18 36 L24 30 L30 36 Z' fill='#FFFFFF' opacity='0.95'/>",
        links=("libreoffice-impress.svg",))
    app("vixzen-startcenter.svg",
        "<circle cx='18' cy='18' r='4' fill='#FFFFFF' opacity='0.95'/>"
        "<circle cx='30' cy='18' r='4' fill='#FFFFFF' opacity='0.7'/>"
        "<circle cx='18' cy='30' r='4' fill='#FFFFFF' opacity='0.7'/>"
        "<circle cx='30' cy='30' r='4' fill='#FFFFFF' opacity='0.95'/>",
        links=("libreoffice-startcenter.svg",))
    # system utilities
    app("vixzen-disks2.svg",
        "<rect x='12' y='18' width='24' height='14' rx='3' " + W + "/>"
        "<circle cx='31' cy='25' r='1.8' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='15' y='22' width='8' height='2' fill='#FFFFFF' opacity='0.7'/>",
        links=("org.gnome.DiskUtility.svg",))
    app("vixzen-logs.svg",
        "".join(f"<rect x='15' y='{14 + i * 6}' width='{18 if i % 2 == 0 else 12}' height='2.6' rx='1.3' fill='#FFFFFF' opacity='0.9'/>"
                for i in range(4)),
        links=("org.gnome.Logs.svg",))
    app("vixzen-tweaks.svg",
        "".join(f"<line x1='14' y1='{17 + i * 7}' x2='34' y2='{17 + i * 7}' stroke='#FFFFFF' stroke-width='2' opacity='0.7'/>"
                f"<circle cx='{20 + i * 4}' cy='{17 + i * 7}' r='3' fill='#FFFFFF' opacity='0.95'/>"
                for i in range(3)),
        links=("org.gnome.tweaks.svg",))
    app("vixzen-characters.svg",
        "<circle cx='24' cy='22' r='9' " + W + "/>"
        "<path d='M20 22 Q22 25 24 22 Q26 19 28 22' stroke='#FFFFFF' stroke-width='2' fill='none'/>",
        links=("org.gnome.Characters.svg",))
    app("vixzen-fonts.svg",
        "<text x='24' y='32' font-family='sans-serif' font-size='20' font-weight='bold' "
        "fill='#FFFFFF' text-anchor='middle'>Aa</text>",
        links=("org.gnome.font-viewer.svg",))
    app("vixzen-clocks.svg",
        "<circle cx='24' cy='24' r='11' " + W + "/>"
        "<line x1='24' y1='24' x2='24' y2='16' stroke='#FFFFFF' stroke-width='2.4'/>"
        "<line x1='24' y1='24' x2='29' y2='26' stroke='#FFFFFF' stroke-width='2.4'/>",
        links=("org.gnome.clocks.svg",))
    app("vixzen-weather.svg",
        "<circle cx='30' cy='17' r='5' fill='#FFFFFF' opacity='0.95'/>"
        "<path d='M14 32 Q14 25 21 25 Q23 20 28 21 Q34 22 34 28 Q34 32 30 32 Z' fill='#FFFFFF' opacity='0.9'/>",
        links=("org.gnome.Weather.svg",))
    app("vixzen-help.svg",
        "<circle cx='24' cy='24' r='11' " + W + "/>"
        "<text x='24' y='31' font-family='sans-serif' font-size='16' font-weight='bold' "
        "fill='#FFFFFF' text-anchor='middle'>?</text>",
        links=("org.gnome.Yelp.svg",))
    app("vixzen-tour.svg",
        "<path d='M24 10 L30 28 L24 25 L18 28 Z' fill='#FFFFFF' opacity='0.95'/>"
        "<circle cx='24' cy='19' r='2' fill='#00A651'/>",
        links=("org.gnome.Tour.svg",))
    app("vixzen-papers.svg",
        "<path d='M15 6 H27 L33 12 V42 H15 Z' " + W + "/>"
        "<circle cx='24' cy='26' r='5' " + W + "/>",
        links=("org.gnome.Papers.svg",))
    app("vixzen-scan.svg",
        "<rect x='12' y='15' width='24' height='18' rx='3' " + W + "/>"
        "<line x1='15' y1='22' x2='33' y2='22' stroke='#FFFFFF' stroke-width='2'/>",
        links=("org.gnome.SimpleScan.svg",))
    app("vixzen-connections.svg",
        "<path d='M17 30 Q17 20 24 20 Q31 20 31 30' " + W + "/>"
        "<rect x='15' y='29' width='4' height='7' rx='2' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='29' y='29' width='4' height='7' rx='2' fill='#FFFFFF' opacity='0.95'/>",
        links=("org.gnome.Connections.svg",))
    app("vixzen-tecla.svg",
        "<rect x='12' y='17' width='24' height='14' rx='3' " + W + "/>"
        "".join(f"<rect x='{16 + i * 5}' y='21' width='3' height='3' fill='#FFFFFF' opacity='0.9'/>" for i in range(4)),
        links=("org.gnome.Tecla.svg",))
    app("vixzen-extensions2.svg",
        "<rect x='13' y='13' width='10' height='10' rx='2' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='25' y='13' width='10' height='10' rx='2' fill='#FFFFFF' opacity='0.6'/>"
        "<rect x='13' y='25' width='10' height='10' rx='2' fill='#FFFFFF' opacity='0.6'/>"
        "<rect x='25' y='25' width='10' height='10' rx='2' fill='#FFFFFF' opacity='0.95'/>",
        links=("org.gnome.Shell.Extensions.svg",))
    app("vixzen-malcontent.svg",
        "<path d='M24 12 L33 16 V24 Q33 32 24 36 Q15 32 15 24 V16 Z' " + W + "/>"
        "<line x1='24' y1='19' x2='24' y2='27' stroke='#FFFFFF' stroke-width='2.4'/>",
        links=("org.freedesktop.MalcontentControl.svg",))
    app("vixzen-installer.svg",
        "<rect x='14' y='14' width='20' height='22' rx='3' " + W + "/>"
        "<path d='M24 19 V29 M20 25 L24 29 L28 25' stroke='#FFFFFF' stroke-width='2.4' fill='none'/>",
        links=("org.fedoraproject.AnacondaInstaller.svg",
               "org.fedoraproject.MediaWriter.svg"))
    app("vixzen-connector.svg",
        "<rect x='20' y='12' width='8' height='12' rx='2' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='17' y='24' width='14' height='12' rx='3' " + W + "/>",
        links=("org.gnome.BrowserConnector.svg",))
    app("vixzen-alarm.svg",
        "<path d='M18 30 A7 7 0 0 1 30 30' " + W + "/>"
        "<line x1='24' y1='30' x2='24' y2='36' stroke='#FFFFFF' stroke-width='2.4'/>"
        "<line x1='15' y1='12' x2='18' y2='16' stroke='#FFFFFF' stroke-width='2.4'/>"
        "<line x1='33' y1='12' x2='30' y2='16' stroke='#FFFFFF' stroke-width='2.4'/>",
        links=("org.gnome.Evolution-alarm-notify.svg",))
    app("vixzen-captive.svg",
        "<circle cx='24' cy='22' r='9' " + W + "/>"
        "<rect x='21' y='30' width='6' height='8' rx='1.5' fill='#FFFFFF' opacity='0.95'/>",
        links=("org.gnome.Shell.CaptivePortal.svg",))
    app("vixzen-orca.svg",
        "<path d='M10 28 Q20 18 30 24 Q36 27 38 22 Q40 28 34 32 Q24 38 10 28 Z' fill='#FFFFFF' opacity='0.95'/>",
        links=("orca.svg",))
    app("vixzen-ibus.svg",
        "<rect x='12' y='15' width='24' height='14' rx='3' " + W + "/>"
        "<circle cx='32' cy='32' r='6' fill='#FFFFFF' opacity='0.95'/>"
        "<path d='M30 32 Q32 29 34 32' stroke='#00A651' stroke-width='1.6' fill='none'/>",
        links=("ibus-setup.svg", "ibus-anthy.svg", "ibus-setup-hangul.svg",
               "ibus-typing-booster.svg", "org.freedesktop.IBus.Chewing.Setup.svg"))
    app("vixzen-bluetooth.svg",
        "<path d='M20 12 L28 20 L22 24 L28 28 L20 36 M20 12 V36 M25 17 L31 12 M25 31 L31 36' "
        "stroke='#FFFFFF' stroke-width='2.4' fill='none'/>",
        links=("bluetooth.svg",))
    app("vixzen-chromium.svg",
        "<circle cx='24' cy='24' r='11' " + W + "/>"
        "<circle cx='24' cy='24' r='4' fill='#FFFFFF' opacity='0.95'/>",
        links=("chromium-browser.svg",))
    app("vixzen-retroterm.svg",
        "<rect x='13' y='12' width='22' height='18' rx='4' " + W + "/>"
        "<path d='M18 19 h7 M18 23 h10' stroke='#FFFFFF' stroke-width='2'/>"
        "<rect x='20' y='32' width='8' height='3' rx='1.5' fill='#FFFFFF' opacity='0.95'/>",
        links=("cool-retro-term.svg",))
    app("vixzen-scrcpy.svg",
        "<rect x='18' y='10' width='12' height='24' rx='3' " + W + "/>"
        "<path d='M22 30 L26 27 L22 24' stroke='#FFFFFF' stroke-width='1.8' fill='none'/>",
        links=("scrcpy.svg", "scrcpy-console.svg"))
    app("vixzen-vm.svg",
        "<rect x='12' y='14' width='24' height='16' rx='2' " + W + "/>"
        "<rect x='20' y='32' width='8' height='3' rx='1.5' fill='#FFFFFF' opacity='0.95'/>"
        "<circle cx='24' cy='22' r='3' fill='#FFFFFF' opacity='0.9'/>",
        links=("virt-viewer.svg", "virtualbox.svg", "org.gnome.Boxes.svg"))
    app("vixzen-opencode.svg",
        "<path d='M16 17 L25 24 L16 31' stroke='#FFFFFF' stroke-width='3' fill='none'/>"
        "<line x1='27' y1='31' x2='34' y2='31' stroke='#FFFFFF' stroke-width='3'/>",
        links=("ai.opencode.desktop.svg",))
    app("vixzen-wine.svg",
        "<path d='M19 11 H29 V24 Q29 30 24 30 Q19 30 19 24 Z' " + W + "/>"
        "<line x1='24' y1='30' x2='24' y2='35' stroke='#FFFFFF' stroke-width='2.4'/>"
        "<line x1='20' y1='37' x2='28' y2='37' stroke='#FFFFFF' stroke-width='2.4'/>",
        links=("wine.svg", "winecfg.svg", "winefile.svg", "winhelp.svg",
               "msiexec.svg"))
    app("vixzen-notepad.svg",
        "<path d='M15 6 H27 L33 12 V42 H15 Z' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='18' y='18' width='12' height='2' fill='#00A651'/>"
        "<rect x='18' y='23' width='12' height='2' fill='#00A651'/>"
        "<rect x='18' y='28' width='7' height='2' fill='#00A651'/>",
        links=("notepad.svg", "wordpad.svg"))
    app("vixzen-regedit.svg",
        "<rect x='14' y='12' width='20' height='24' rx='2' fill='#FFFFFF' opacity='0.95'/>"
        "<rect x='17' y='15' width='7' height='18' fill='#00A651' opacity='0.85'/>"
        "<rect x='25' y='15' width='6' height='18' fill='#00A651' opacity='0.5'/>",
        links=("regedit.svg",))
    app("vixzen-mine.svg",
        ("<circle cx='24' cy='24' r='8' fill='#FFFFFF' opacity='0.95'/>"
         + "".join(f"<line x1='24' y1='24' x2='{24 + dx}' y2='{24 + dy}' stroke='#00A651' stroke-width='2'/>"
                   for dx, dy in ((0, -11), (0, 11), (-11, 0), (11, 0)))),
        links=("winemine.svg",))
    app("vixzen-prefs.svg",
        "<circle cx='24' cy='24' r='4' fill='#FFFFFF' opacity='0.95'/>"
        "<circle cx='24' cy='24' r='10' " + W + "/>",
        links=("preferences-system.svg",))
    app("vixzen-removable.svg",
        "<rect x='16' y='12' width='16' height='10' rx='2' " + W + "/>"
        "<rect x='20' y='24' width='8' height='10' rx='1.5' fill='#FFFFFF' opacity='0.9'/>",
        links=("drive-removable-media.svg",))
    app("vixzen-newdoc.svg",
        "<path d='M15 6 H27 L33 12 V42 H15 Z' " + W + "/>"
        "<path d='M24 16 V26 M19 21 H29' stroke='#FFFFFF' stroke-width='2.4'/>",
        links=("document-new.svg",))
    app("vixzen-print.svg",
        "<rect x='17' y='12' width='14' height='8' rx='1.5' fill='#FFFFFF' opacity='0.9'/>"
        "<rect x='14' y='18' width='20' height='12' rx='2' " + W + "/>"
        "<rect x='17' y='30' width='14' height='7' rx='1.5' fill='#FFFFFF' opacity='0.9'/>",
        links=("document-print-preview.svg",))
    app("vixzen-shield.svg",
        "<path d='M24 10 L34 14 V24 Q34 33 24 38 Q14 33 14 24 V14 Z' " + W + "/>"
        "<path d='M20 24 L23 27 L28 21' stroke='#FFFFFF' stroke-width='2.4' fill='none'/>",
        links=("security-medium.svg",))
    # mimetypes, extra
    mime_doc = os.path.join(MIME, "application-vnd.iccprofile.svg")
    save(mime_doc,
         "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
         "<path d='M12 4 H30 L38 12 V44 H12 Z' fill='#FFFFFF'/>"
         "<path d='M30 4 L38 12 H30 Z' fill='#D1FAE5'/>"
         "<circle cx='24' cy='24' r='4' fill='#EA580C'/>"
         "<circle cx='24' cy='24' r='7' fill='none' stroke='#EA580C' stroke-width='2' opacity='0.6'/>")
    print(f"part 3 complete: apps + 1 mimetype (see {APPS})")


if __name__ == "__main__":
    main()
