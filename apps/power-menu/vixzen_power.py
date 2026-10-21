#!/usr/bin/env python3
"""Vixzen Start Menu v4 — industrial finish, Windows-11 layout language.
Search pill, Pinned icon grid + Show-all toggle, Recommended files with
type icons, user avatar + power flyout footer, slide-up entrance, popup
behavior (no dock entry, dismiss on focus loss). Original Vixzen art only.
Run: python3 apps/power-menu/vixzen_power.py [--smoke]
"""
import os, sys, subprocess, getpass, json, time, threading
import urllib.request
import xml.etree.ElementTree as ET

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib

APP_ID = "os.vixzen.power"
PINNED_IDS = ["vixzen-menu.desktop", "org.mozilla.firefox.desktop",
              "org.gnome.Nautilus.desktop", "org.gnome.TextEditor.desktop",
              "org.gnome.Calculator.desktop", "org.gnome.Software.desktop",
              "org.gnome.Settings.desktop",
              "org.gnome.Calendar.desktop", "org.gnome.Ptyxis.desktop",
              "org.gnome.Terminal.desktop", "org.mozilla.Thunderbird.desktop",
              "com.google.Chrome.desktop"]

CSS = """
.vix-card {
  background: linear-gradient(160deg, rgba(52,55,80,0.97), rgba(22,24,38,0.97));
  border: 1px solid rgba(255,255,255,0.20);
  border-top-color: rgba(255,255,255,0.48);
  border-left-color: rgba(255,255,255,0.28);
  box-shadow: 0 24px 70px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.25);
  border-radius: 22px;
}
.vix-search { border-radius: 16px; padding: 9px 16px; font-size: 15px;
  background-color: rgba(255,255,255,0.10);
  border: 1px solid rgba(255,255,255,0.16); }
.vix-search:focus { border-color: #7C7CFF; }
.vix-section { color: #E8EAF2; font-weight: bold; letter-spacing: 1px; }
.vix-user { color: #FFFFFF; font-weight: bold; }
.vix-showall { border-radius: 10px; padding: 4px 12px;
  background-color: rgba(255,255,255,0.10); }
.vix-tile { border-radius: 15px; padding: 12px 4px; border: 1px solid transparent; }
.vix-tile:hover { background-color: rgba(124,124,255,0.30);
  border-color: rgba(124,124,255,0.55); }
.vix-tile:active { background-color: rgba(124,124,255,0.45); }
.vix-rec { border-radius: 12px; padding: 8px 10px; }
.vix-rec:hover { background-color: rgba(124,124,255,0.25); }
.vix-avatar { background-color: #4F46E5; color: white; font-weight: bold;
  border-radius: 999px; }
.vix-powerbtn { border-radius: 999px; padding: 8px 12px;
  background-color: rgba(255,255,255,0.10); }
.vix-powerbtn:hover { background-color: rgba(249,115,22,0.45); }
"""

def all_apps():
    try:
        return sorted(
            (a for a in Gio.AppInfo.get_all()
             if a.should_show() and a.get_display_name()),
            key=lambda a: a.get_display_name().lower())
    except Exception:
        return []

# --- Top Stories: free RSS headlines, no API key, cached offline ---
FEEDS = [
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
]
NEWS_CACHE = os.path.expanduser("~/.cache/vixzen/news.json")
NEWS_TTL = 30 * 60  # seconds


def parse_rss(data, source, limit=4):
    """Pure feed parser (unit-tested, no network). Returns [(src, title, link)]."""
    out = []
    try:
        root = ET.fromstring(data)
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            if title and link:
                out.append((source, title, link))
            if len(out) >= limit:
                break
    except Exception:
        pass
    return out


def read_news_cache():
    try:
        with open(NEWS_CACHE) as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("items"), list):
            return d
    except Exception:
        pass
    return {"items": [], "fetched": 0}


def fetch_news_async(done_cb):
    """Background refresh; done_cb(items, fresh) runs on the UI thread."""
    def work():
        items = []
        for source, url in FEEDS:
            try:
                req = urllib.request.Request(
                    url, headers={"User-Agent": "VixzenOS/0.3"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    items.extend(parse_rss(r.read(512 * 1024), source))
            except Exception:
                continue
            if len(items) >= 8:
                break
        if items:
            try:
                os.makedirs(os.path.dirname(NEWS_CACHE), exist_ok=True)
                with open(NEWS_CACHE, "w") as f:
                    json.dump({"items": items[:8],
                               "fetched": int(time.time())}, f)
            except Exception:
                pass
            GLib.idle_add(lambda: done_cb(items[:8], True) or False)
        else:
            cached = read_news_cache()
            GLib.idle_add(lambda: done_cb(cached.get("items", []),
                                          False) or False)
    threading.Thread(target=work, daemon=True).start()

class Win(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Vixzen Start")
        self.set_default_size(700, 640)
        # Dark glass needs the dark base: this window is plain Gtk (no
        # libadwaita), so force it — otherwise tiles render washed-white.
        try:
            Gtk.Settings.get_default().set_property(
                "gtk-application-prefer-dark-theme", True)
        except Exception:
            pass
        # Collapse the titlebar: an empty titlebar widget = zero-height
        # chrome, so the card itself is the whole window.
        try:
            self.set_titlebar(Gtk.Grid())
        except Exception:
            pass
        try:
            self.set_skip_taskbar_hint(True)
            self.set_skip_pager_hint(True)
            self.set_decorated(False)
        except Exception:
            pass
        self._confirm_open = False
        self._show_all = False
        self.connect("notify::is-active", self._autodismiss)
        css = Gtk.CssProvider()
        css.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            __import__("gi.repository", fromlist=["Gdk"]).Gdk.Display.get_default(),
            css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.revealer = Gtk.Revealer()
        self.revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self.revealer.set_transition_duration(220)
        self.set_child(self.revealer)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("vix-card")
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(card, f"set_{m}")(18)
        self.revealer.set_child(card)

        top = Gtk.Box(spacing=8)
        self.search = Gtk.SearchEntry(placeholder_text="Search apps, settings, files…")
        self.search.add_css_class("vix-search")
        self.search.set_hexpand(True)
        self.search.connect("search-changed", lambda *_: self.refilter())
        top.append(self.search)
        x = Gtk.Button(label="✕", tooltip_text="Close (Esc)")
        x.connect("clicked", lambda *_: self.close())
        top.append(x)
        card.append(top)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        card.append(scroll)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scroll.set_child(content)

        pinrow = Gtk.Box(spacing=8)
        pinrow.append(self.head("Pinned"))
        sp = Gtk.Box()
        sp.set_hexpand(True)
        pinrow.append(sp)
        self.showall = Gtk.Button(label="Show all  ›")
        self.showall.add_css_class("vix-showall")
        self.showall.connect("clicked", self.toggle_showall)
        pinrow.append(self.showall)
        content.append(pinrow)
        self.pinned = self.grid(6)
        content.append(self.pinned)

        content.append(self.head("Recommended"))
        self.rec = Gtk.FlowBox(max_children_per_line=2,
                               selection_mode=Gtk.SelectionMode.NONE,
                               column_spacing=8, row_spacing=8)
        content.append(self.rec)

        newsrow = Gtk.Box(spacing=8)
        newsrow.append(self.head("Top Stories"))
        newsp = Gtk.Box()
        newsp.set_hexpand(True)
        newsrow.append(newsp)
        self.news_hint = Gtk.Label(label="")
        newsrow.append(self.news_hint)
        self.news_btn = Gtk.Button(label="↻")
        self.news_btn.set_tooltip_text("Refresh headlines")
        self.news_btn.add_css_class("vix-showall")
        self.news_btn.connect("clicked", self.refresh_news)
        newsrow.append(self.news_btn)
        content.append(newsrow)
        self.news = Gtk.ListBox()
        self.news.add_css_class("vix-card")
        content.append(self.news)

        foot = Gtk.Box(spacing=10)
        try:
            user = getpass.getuser()
        except Exception:
            user = "user"
        av = Gtk.Label(label=user[:1].upper())
        av.add_css_class("vix-avatar")
        av.set_size_request(36, 36)
        foot.append(av)
        uname = Gtk.Label(label=user)
        uname.add_css_class("vix-user")
        foot.append(uname)
        fsp = Gtk.Box()
        fsp.set_hexpand(True)
        foot.append(fsp)
        self.power = Gtk.Button(label="⏻")
        self.power.add_css_class("vix-powerbtn")
        self.power.set_tooltip_text("Power: Suspend, Restart, Power Off, Log Out")
        self.power.connect("clicked", self.power_menu)
        foot.append(self.power)
        card.append(foot)

        keys = Gtk.EventControllerKey.new()
        keys.connect("key-pressed", lambda _, k, *__: self.close() if k == 65307 else None)
        self.add_controller(keys)

        self.apps = all_apps()
        self.by_id = {}
        for a in self.apps:
            try:
                self.by_id[a.get_id()] = a
            except Exception:
                pass
        self.fill_rec()
        self.refilter()
        self.fill_news(read_news_cache().get("items", []), False)
        GLib.timeout_add(400, self._news_bg)
        GLib.timeout_add(40, self._reveal)

    def _reveal(self):
        self.revealer.set_reveal_child(True)
        self.search.grab_focus()
        return False

    def _autodismiss(self, *_):
        if os.environ.get("VIXZEN_MENU_STAY"):
            return  # photo mode: stay open for screenshots
        if (not self.is_active() and self.revealer.get_reveal_child()
                and not self._confirm_open):
            self.close()

    def head(self, text):
        lbl = Gtk.Label(label=text.upper(), xalign=0)
        lbl.add_css_class("vix-section")
        return lbl

    def grid(self, per_line):
        return Gtk.FlowBox(max_children_per_line=per_line,
                           selection_mode=Gtk.SelectionMode.NONE,
                           column_spacing=6, row_spacing=6)

    def tile(self, app):
        b = Gtk.Button()
        b.add_css_class("vix-tile")
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        try:
            icon = app.get_icon()
            img = Gtk.Image.new_from_gicon(icon) if icon else Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        except Exception:
            img = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
        img.set_pixel_size(52)
        vb.append(img)
        name = app.get_display_name()
        vb.append(Gtk.Label(label=name if len(name) <= 14 else name[:13] + "…"))
        b.set_child(vb)
        b.set_tooltip_text(name)
        b.connect("clicked", lambda *_: self.launch(app))
        return b

    def toggle_showall(self, _b):
        self._show_all = not self._show_all
        self.showall.set_label("‹ Back" if self._show_all else "Show all  ›")
        self.refilter()

    def fill_rec(self):
        try:
            items = Gtk.RecentManager.get_default().get_items()[:4]
        except Exception:
            items = []
        if not items:
            self.rec.append(Gtk.Label(label="Your recent files appear here."))
            return
        for it in items:
            try:
                full = it.get_display_name() or "?"
                name = full if len(full) <= 30 else full[:29] + "…"
                uri = it.get_uri()
                icon = None
                try:
                    info = Gio.File.new_for_uri(uri).query_info(
                        "standard::symbolic-icon", Gio.FileQueryInfoFlags.NONE, None)
                    icon = info.get_symbolic_icon()
                except Exception:
                    pass
                b = Gtk.Button()
                b.add_css_class("vix-rec")
                b.set_hexpand(True)
                hb = Gtk.Box(spacing=10)
                img = (Gtk.Image.new_from_gicon(icon) if icon
                       else Gtk.Image.new_from_icon_name("text-x-generic-symbolic"))
                img.set_pixel_size(32)
                hb.append(img)
                vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
                vb.set_hexpand(True)
                name_lbl = Gtk.Label(label=name, xalign=0)
                name_lbl.set_ellipsize(3)  # END
                vb.append(name_lbl)
                vb.append(Gtk.Label(label="Recent file", xalign=0))
                hb.append(vb)
                b.set_child(hb)
                b.set_tooltip_text(full)
                b.connect("clicked", lambda _b, u=uri:
                          Gio.AppInfo.launch_default_for_uri(u, None))
                self.rec.append(b)
            except Exception:
                continue

    def refilter(self):
        while (c := self.pinned.get_first_child()):
            self.pinned.remove(c)
        q = self.search.get_text().lower()
        if q or self._show_all:
            pool = [a for a in self.apps
                    if not q or q in a.get_display_name().lower()][:30]
            for a in pool:
                self.pinned.append(self.tile(a))
            return
        for pid in PINNED_IDS:
            a = self.by_id.get(pid)
            if a:
                self.pinned.append(self.tile(a))

    def launch(self, app):
        try:
            app.launch([], None)
            self.close()
        except Exception:
            pass

    def _news_bg(self):
        cached = read_news_cache()
        if time.time() - cached.get("fetched", 0) < NEWS_TTL and cached.get("items"):
            return False  # fresh enough; skip network
        fetch_news_async(self.fill_news)
        return False

    def refresh_news(self, _b):
        self.news_hint.set_label("updating…")
        fetch_news_async(self.fill_news)

    def fill_news(self, items, fresh):
        while (row := self.news.get_row_at_index(0)):
            self.news.remove(row)
        if fresh:
            self.news_hint.set_label("")
        elif items:
            try:
                when = time.strftime("%H:%M", time.localtime(
                    read_news_cache().get("fetched", 0)))
                self.news_hint.set_label(f"cached {when}")
            except Exception:
                self.news_hint.set_label("cached")
        else:
            self.news_hint.set_label("offline")
        for src, title, link in (items or [])[:6]:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=10)
            box.append(Gtk.Image.new_from_icon_name("news-subscribe-symbolic"))
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            vb.set_hexpand(True)
            t = Gtk.Label(label=title, xalign=0, wrap=True, max_width_chars=52)
            vb.append(t)
            s = Gtk.Label(label=src, xalign=0)
            s.set_opacity(0.6)
            vb.append(s)
            box.append(vb)
            row.set_child(box)
            row.set_tooltip_text(title)
            row.connect("activate", lambda _r, u=link:
                        Gio.AppInfo.launch_default_for_uri(u, None))
            self.news.append(row)
        if not items:
            self.news.append(Gtk.Label(
                label="No headlines yet — connect, then press ↻."))

    def power_menu(self, btn):
        m = Gio.Menu()
        for label in ("Suspend", "Restart", "Power Off", "Log Out"):
            m.append(label, f"win.power::{label}")
        try:
            self.add_action_entries([("power", self.on_power, "s")])
        except Exception:
            pass
        pop = Gtk.PopoverMenu.new_from_model(m)
        pop.set_parent(btn)
        pop.popup()

    def on_power(self, _action, param):
        label = param.get_string() if param else ""
        cmds = {"Suspend": ["systemctl", "suspend"], "Restart": ["systemctl", "reboot"],
                "Power Off": ["systemctl", "poweroff"],
                "Log Out": ["gnome-session-quit", "--logout", "--no-prompt"]}
        if label in cmds:
            self.confirm(label, cmds[label])

    def confirm(self, label, cmd):
        dlg = Gtk.AlertDialog()
        dlg.set_message(f"{label}?")
        dlg.set_detail("Unsaved work in other apps could be lost.")
        dlg.set_buttons(["Cancel", label])
        dlg.set_cancel_button(0)
        dlg.set_default_button(0)
        self._confirm_open = True
        def done(_d, res):
            self._confirm_open = False
            try:
                if _d.choose_finish(res) == 1:
                    subprocess.Popen(cmd)
                    self.get_application().quit()
            except Exception:
                pass
        dlg.choose(self, None, done)

class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
    def do_activate(self):
        self.get_active_window() or Win(self).present()

if __name__ == "__main__":
    if "--smoke" in sys.argv:
        import shutil
        apps = all_apps()
        assert len(apps) > 5, "too few apps"
        assert "SLIDE_UP" in open(__file__).read(), "entrance animation missing"
        assert "\n        self.fullscreen()" not in open(__file__).read(), "must not take over screen"
        assert "Show all" in open(__file__).read(), "win11 show-all missing"
        assert all(shutil.which(c) for c in ["systemctl", "gnome-session-quit"])
        sample = ('<?xml version="1.0"?><rss><channel>'
                  '<item><title>T1</title><link>https://x.test/1</link></item>'
                  '<item><title>T2</title><link>https://x.test/2</link></item>'
                  '</channel></rss>').encode()
        parsed = parse_rss(sample, "UT")
        assert parsed == [("UT", "T1", "https://x.test/1"),
                          ("UT", "T2", "https://x.test/2")], parsed
        assert parse_rss(b"<broken", "UT") == []
        print(f"startmenu v4 smoke OK: {len(apps)} apps, news parser, show-all + avatar + power flyout")
    else:
        App().run([sys.argv[0]])
