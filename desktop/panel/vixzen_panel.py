#!/usr/bin/env python3
"""Vixzen Host Panel — a REAL bottom bar on your host desktop (no logout).

Anchored via gtk4-layer-shell: full-width, 46px, exclusive zone (maximized
windows respect it). Launcher with real app search, pinned real apps,
live clock. Honest limits: it cannot minimize/switch windows (only the
GNOME extension, after a relogin, can do that).

Run:   python3 desktop/panel/vixzen_panel.py
Stop:  right-click the bar → Quit  (or: pkill -f vixzen_panel)
Smoke: python3 desktop/panel/vixzen_panel.py --smoke  (headless checks)
Requires: gtk4-layer-shell (tiny, already installed per user approval).
"""
import os, sys, datetime, json, time, threading
import urllib.request

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
gi.require_version("GioUnix", "2.0")
from gi.repository import Gtk, GLib, Gio, GioUnix, Gtk4LayerShell as Layer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "preview", "src"))
from design import css_for

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "apps", "power-menu"))
from vixzen_power import FEEDS, NEWS_TTL, parse_rss, read_news_cache

WX_CACHE = os.path.expanduser("~/.cache/vixzen/weather.json")
WX_TTL = 30 * 60

WMO = {0: ("☀", "Clear"), 1: ("🌤", "Mainly clear"), 2: ("⛅", "Partly cloudy"),
       3: ("☁", "Overcast"), 45: ("🌫", "Fog"), 48: ("🌫", "Icy fog"),
       51: ("🌦", "Light drizzle"), 53: ("🌦", "Drizzle"),
       55: ("🌦", "Heavy drizzle"), 56: ("🌧", "Freezing drizzle"),
       57: ("🌧", "Freezing drizzle"), 61: ("🌧", "Light rain"),
       63: ("🌧", "Rain"), 65: ("🌧", "Heavy rain"), 66: ("🌧", "Freezing rain"),
       67: ("🌧", "Freezing rain"), 71: ("❄", "Light snow"),
       73: ("❄", "Snow"), 75: ("❄", "Heavy snow"), 77: ("❄", "Snow grains"),
       80: ("🌦", "Light showers"), 81: ("🌦", "Showers"),
       82: ("🌦", "Violent showers"), 85: ("❄", "Snow showers"),
       86: ("❄", "Snow showers"), 95: ("⛈", "Thunderstorm"),
       96: ("⛈", "Storm + hail"), 99: ("⛈", "Storm + hail")}


def read_wx_cache():
    try:
        with open(WX_CACHE) as f:
            d = json.load(f)
        if isinstance(d, dict) and "temp" in d:
            return d
    except Exception:
        pass
    return {}


def fetch_weather_async(done_cb):
    """IP location -> Open-Meteo (both keyless). done_cb(dict) on UI thread."""
    def work():
        out = {}
        try:
            with urllib.request.urlopen(
                    "http://ip-api.com/json/?fields=lat,lon,city",
                    timeout=8) as r:
                loc = json.load(r)
            lat, lon, city = loc["lat"], loc["lon"], loc.get("city", "")
            url = ("https://api.open-meteo.com/v1/forecast?latitude=%s"
                   "&longitude=%s&current=temperature_2m,weather_code" % (lat, lon))
            with urllib.request.urlopen(url, timeout=8) as r:
                cur = json.load(r)["current"]
            out = {"temp": round(cur["temperature_2m"]), "code": cur["weather_code"],
                   "city": city, "fetched": int(time.time())}
            os.makedirs(os.path.dirname(WX_CACHE), exist_ok=True)
            with open(WX_CACHE, "w") as f:
                json.dump(out, f)
        except Exception:
            pass
        GLib.idle_add(lambda: done_cb(out) or False)
    threading.Thread(target=work, daemon=True).start()

APP_ID = "os.vixzen.panel"
PINNED = [
    ("Files", ["org.gnome.Nautilus", "org.gnome.Files"]),
    ("Terminal", ["org.gnome.Ptyxis", "org.gnome.Terminal", "org.gnome.Console"]),
    ("Browser", ["org.mozilla.firefox", "org.gnome.Epiphany"]),
    ("Software", ["org.gnome.Software"]),
    ("Settings", ["org.gnome.Settings"]),
]

def resolve(ids):
    for i in ids:
        try:
            app = GioUnix.DesktopAppInfo.new(i + ".desktop")
            if app:
                return app
        except Exception:
            continue
    return None

class Panel(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Vixzen Panel")
        css = Gtk.CssProvider()
        css.load_from_data(css_for("dark", "balanced").encode())
        Gtk.StyleContext.add_provider_for_display(
            __import__("gi.repository", fromlist=["Gdk"]).Gdk.Display.get_default(),
            css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Anchor to bottom of the screen, above windows, reserve space.
        Layer.init_for_window(self)
        Layer.set_layer(self, Layer.Layer.TOP)
        Layer.set_anchor(self, Layer.Edge.BOTTOM, True)
        Layer.set_anchor(self, Layer.Edge.LEFT, True)
        Layer.set_anchor(self, Layer.Edge.RIGHT, True)
        Layer.set_exclusive_zone(self, 46)
        Layer.set_keyboard_mode(self, Layer.KeyboardMode.NONE)

        bar = Gtk.Box(spacing=8)
        bar.add_css_class("vix-taskbar")
        bar.set_size_request(-1, 46)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(bar, f"set_{m}")(4)
        self.set_child(bar)

        launch = Gtk.Button()
        launch.add_css_class("vix-accent")
        launch_box = Gtk.Box(spacing=6)
        logo_file = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "branding", "logo.svg"))
        if os.path.exists(logo_file):
            logo_img = Gtk.Image.new_from_file(logo_file)
            logo_img.set_pixel_size(22)
            launch_box.append(logo_img)
        launch_box.append(Gtk.Label(label="Vixzen"))
        launch.set_child(launch_box)
        launch.set_tooltip_text("Vixzen menu — apps + power (Shutdown, Restart, Suspend, Log Out)")
        launch.connect("clicked", self.open_launcher)
        bar.append(launch)

        for name, ids in PINNED:
            info = resolve(ids)
            b = Gtk.Button(tooltip_text=name,
                           icon_name=info.get_icon().to_string() if info and info.get_icon() else "application-x-executable-symbolic")
            b.connect("clicked", lambda _b, i=info, n=name: i.launch([], None) if i else None)
            if info is None:
                b.set_sensitive(False)
            bar.append(b)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)
        self.wx_btn = Gtk.Button(label="⛅ …")
        self.wx_btn.set_tooltip_text("Weather — click for now + city")
        self.wx_btn.connect("clicked", self.open_weather)
        bar.append(self.wx_btn)
        self.head_btn = Gtk.Button(label="📰")
        self.head_btn.set_tooltip_text("Top stories — click for headlines")
        self.head_btn.connect("clicked", self.open_news)
        bar.append(self.head_btn)
        self.clock = Gtk.Label()
        bar.append(self.clock)
        GLib.timeout_add_seconds(1, self.tick)
        self.tick()
        self.wx = read_wx_cache()
        self.paint_weather(cache_only=True)
        GLib.timeout_add(500, self._wx_bg)
        GLib.timeout_add(600, self._news_bg)

        right = Gtk.GestureClick.new()
        right.set_button(3)
        right.connect("pressed", self.on_right)
        self.add_controller(right)

    def tick(self):
        self.clock.set_label(datetime.datetime.now().strftime("%H:%M"))
        return True

    # ---- taskbar weather + headlines (Windows-widget style) ----
    def paint_weather(self, cache_only=False):
        w = getattr(self, "wx", {}) or {}
        if w and time.time() - w.get("fetched", 0) < WX_TTL:
            icon, _text = WMO.get(w.get("code", 3), ("⛅", ""))
            self.wx_btn.set_label(f"{icon} {w.get('temp', '?')}°")
            tip = f"{w.get('city', '')} {_text}".strip()
            self.wx_btn.set_tooltip_text(tip or "Weather")
        elif not cache_only:
            self.wx_btn.set_label("⛅ off")
            self.wx_btn.set_tooltip_text("Offline — cached weather unavailable")

    def _wx_bg(self):
        w = read_wx_cache()
        if w and time.time() - w.get("fetched", 0) < WX_TTL:
            self.wx = w
            self.paint_weather(cache_only=True)
            return False
        fetch_weather_async(self._wx_done)
        return False

    def _wx_done(self, out):
        if out:
            self.wx = out
            self.paint_weather(cache_only=True)
        else:
            self.paint_weather(cache_only=False)

    def _news_bg(self):
        from vixzen_power import fetch_news_async as _fetch
        cached = read_news_cache()
        if time.time() - cached.get("fetched", 0) < NEWS_TTL and cached.get("items"):
            return False
        _fetch(lambda items, fresh: None)
        return False

    def popup_shell(self, title):
        dlg = Gtk.Window(title=title)
        dlg.set_default_size(380, 420)
        dlg.set_transient_for(self)
        dlg.set_modal(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(box, f"set_{m}")(16)
        dlg.set_child(box)
        return dlg, box

    def open_weather(self, _b):
        dlg, box = self.popup_shell("Weather")
        w = getattr(self, "wx", {}) or read_wx_cache()
        icon, text = WMO.get((w or {}).get("code", 3), ("⛅", ""))
        big = Gtk.Label()
        big.set_markup(f"<span size='48000'>{icon}</span>")
        box.append(big)
        box.append(Gtk.Label(label=f"{w.get('temp', '?')}°C — {text}" if w else "Offline"))
        box.append(Gtk.Label(label=w.get("city", "") if w else "No cached forecast"))
        sub = Gtk.Label(label="via Open-Meteo • refreshes every 30 min")
        sub.set_opacity(0.6)
        box.append(sub)
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_: dlg.close())
        box.append(close)
        dlg.present()

    def open_news(self, _b):
        from vixzen_power import fetch_news_async as _fetch
        dlg, box = self.popup_shell("Top Stories")
        box.append(Gtk.Label(label="Latest headlines — click to read"))
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        lst = Gtk.ListBox()
        scroll.set_child(lst)
        box.append(scroll)
        items = read_news_cache().get("items", [])
        if not items:
            lst.append(Gtk.Label(label="Fetching…"))
            _fetch(lambda fresh_items, fresh: GLib.idle_add(
                lambda: (self._fill_popup_news(lst, fresh_items), False)[1]))
        else:
            self._fill_popup_news(lst, items)
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_: dlg.close())
        box.append(close)
        dlg.present()

    def _fill_popup_news(self, lst, items):
        while (row := lst.get_row_at_index(0)):
            lst.remove(row)
        for src, title, link in (items or [])[:8]:
            row = Gtk.ListBoxRow()
            vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            t = Gtk.Label(label=title, xalign=0, wrap=True, max_width_chars=44)
            vb.append(t)
            s = Gtk.Label(label=src, xalign=0)
            s.set_opacity(0.6)
            vb.append(s)
            row.set_child(vb)
            row.connect("activate", lambda _r, u=link:
                        Gio.AppInfo.launch_default_for_uri(u, None))
            lst.append(row)
        if not items:
            lst.append(Gtk.Label(label="Offline — no cached headlines."))

    def on_right(self, _g, _n, x, y):
        pop = Gtk.PopoverMenu.new_from_model(self.quit_menu())
        pop.set_parent(self)
        from gi.repository import Gdk
        pop.set_pointing_to(Gdk.Rectangle(int(x), int(y), 1, 1))
        pop.popup()

    def quit_menu(self):
        m = Gio.Menu()
        m.append("Quit Vixzen Panel", "win.quit")
        q = Gio.SimpleAction.new("quit", None)
        q.connect("activate", lambda *_: self.get_application().quit())
        self.add_action(q)
        return m

    def open_launcher(self, _b):
        dlg = Gtk.Window(title="Vixzen")
        dlg.set_default_size(480, 480)
        dlg.set_transient_for(self)
        dlg.set_modal(True)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(box, f"set_{m}")(12)
        dlg.set_child(box)
        head = Gtk.Label()
        head.set_markup("<b><big>VixzenOS</big></b>  —  Lightweight • Graphical • Yours")
        box.append(head)
        search = Gtk.SearchEntry(placeholder_text="Type to search installed apps…")
        box.append(search)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        grid = Gtk.FlowBox(max_children_per_line=4, selection_mode=Gtk.SelectionMode.NONE)
        scroll.set_child(grid)
        box.append(scroll)
        try:
            apps = sorted(
                (a for a in Gio.AppInfo.get_all()
                 if a.should_show() and a.get_display_name()),
                key=lambda a: a.get_display_name().lower())
        except Exception:
            apps = []
        def fill(q=""):
            while (c := grid.get_first_child()):
                grid.remove(c)
            n = 0
            for a in apps:
                if q and q not in a.get_display_name().lower():
                    continue
                cell = Gtk.Button(label=a.get_display_name())
                cell.connect("clicked",
                             lambda _b, app=a: (app.launch([], None), dlg.close()))
                grid.append(cell)
                n += 1
                if n >= 60:
                    break
        search.connect("search-changed", lambda *_: fill(search.get_text().lower()))
        fill()
        # Windows-style power row: real actions, always behind a confirm dialog.
        box.append(Gtk.Separator())
        power = Gtk.Box(spacing=6)
        power.append(Gtk.Label(label="Power:"))
        for label, cmd in [("⏻ Shut down", ["systemctl", "poweroff"]),
                           ("↻ Restart", ["systemctl", "reboot"]),
                           ("☾ Suspend", ["systemctl", "suspend"]),
                           ("⇥ Log out", ["gnome-session-quit", "--logout", "--no-prompt"])]:
            b = Gtk.Button(label=label)
            b.connect("clicked", lambda _b, l=label, c=cmd: self.confirm_power(dlg, l, c))
            power.append(b)
        box.append(power)
        search.grab_focus()
        dlg.present()

    def confirm_power(self, parent, label, cmd):
        import subprocess
        dlg = Gtk.AlertDialog()
        dlg.set_message(f"{label}?")
        dlg.set_detail("Unsaved work in other apps could be lost. This acts on the real system.")
        dlg.set_buttons(["Cancel", label])
        dlg.set_cancel_button(0)
        dlg.set_default_button(0)
        def done(_d, res):
            try:
                if _d.choose_finish(res) == 1:
                    subprocess.Popen(cmd)
            except Exception:
                pass
        dlg.choose(parent, None, done)

class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
    def do_activate(self):
        win = self.get_active_window()
        (win or Panel(self)).present()

if __name__ == "__main__":
    if "--smoke" in sys.argv:
        resolved = sum(1 for _, ids in PINNED if resolve(ids))
        assert 0 in WMO and 95 in WMO and len(WMO) >= 20, "weather codes incomplete"
        import vixzen_power
        assert callable(vixzen_power.fetch_news_async)
        print(f"panel smoke OK: layer-shell importable, {resolved}/{len(PINNED)} pinned apps resolve, weather+news wired")
    else:
        App().run([sys.argv[0]])
