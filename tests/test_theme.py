"""Theme integrity tests (headless): shell + GTK sheets stay valid CSS,
required Vixzen selectors present, icon/cursor themes well-formed."""
import configparser
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
SHELL = REPO / "assets" / "shell-theme" / "gnome-shell.css"
GTK = REPO / "assets" / "gtk-theme"
REQUIRED_SHELL = [".message", ".message-title", ".quick-settings",
                  ".quick-toggle:checked", ".events-button",
                  ".calendar-today", "#panel"]


def _balanced(path):
    txt = pathlib.Path(path).read_text()
    # strip comments to avoid brace false-positives
    txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
    assert txt.count("{") == txt.count("}"), (path, "unbalanced braces")
    assert txt.count("{") > 5, (path, "suspiciously empty")
    return txt


def test_shell_css():
    txt = _balanced(SHELL)
    assert '@import url("resource:///org/gnome/shell/theme/gnome-shell.css")' in txt
    for sel in REQUIRED_SHELL:
        assert sel in txt, f"missing selector {sel}"


def test_gtk_css():
    for name in ("vixzen-gtk.css", "vixzen-gtk-dark.css",
                 "vixzen-gtk-neon.css"):
        p = GTK / name
        if name == "vixzen-gtk-neon.css" and not p.is_file():
            continue
        _balanced(p)


def test_icon_theme():
    idx = REPO / "assets" / "icons" / "theme" / "Vixzen" / "index.theme"
    cp = configparser.ConfigParser()
    cp.read(idx)
    assert cp.get("Icon Theme", "Name") == "Vixzen"
    assert "Adwaita" in cp.get("Icon Theme", "Inherits")
    apps = REPO / "assets" / "icons" / "theme" / "Vixzen" / "scalable" / "apps"
    svgs = list(apps.glob("*.svg"))
    assert len(svgs) >= 20, f"only {len(svgs)} app icons"
    for must in ("vixzen-browser.svg", "firefox.svg",
                 "org.mozilla.firefox.svg"):
        assert (apps / must).is_file(), must
    mime = REPO / "assets" / "icons" / "theme" / "Vixzen" / "scalable" / "mimetypes"
    assert mime.is_dir()
    for must in ("text-x-generic.svg", "video-x-generic.svg",
                 "application-pdf.svg"):
        assert (mime / must).is_file(), must
    assert len(list(mime.glob("*.svg"))) >= 7
    assert "scalable/mimetypes" in (REPO / "assets" / "icons" / "theme" /
                                    "Vixzen" / "index.theme").read_text()


def test_cursor_assets():
    mc = REPO / "assets" / "cursors" / "McMojave"
    if not mc.is_dir():
        return
    assert (mc / "index.theme").is_file()
    assert (mc / "cursors" / "left_ptr").is_file()


if __name__ == "__main__":
    test_shell_css()
    test_gtk_css()
    test_icon_theme()
    test_cursor_assets()
    print("theme tests OK: 4 checks passed")
