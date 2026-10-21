#!/usr/bin/env python3
"""VixzenOS Preview v0.2 — safe interactive prototype (mock data only).

Run: python3 preview/src/vixzen_preview.py [--smoke]
New in v0.2: active-app indicators on taskbar, keyboard shortcuts
(Super launcher, Alt+1..4 pages, 1..6 apps), wallpaper picker, tray mocks,
file search filter + breadcrumb, theme/perf/wallpaper persisted to
~/.config/vixzen/preview.json (config only — never touches user files).
"""
import os, sys, json, datetime

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk, Gio

sys.path.insert(0, os.path.dirname(__file__))
from design import THEMES, WALLPAPERS, ACCENTS, LIQUID_CARD, css_for

APP_ID = "os.vixzen.preview"
APPS = [
    ("Files", "folder-symbolic"),
    ("Terminal", "terminal-symbolic"),
    ("Browser", "web-browser-symbolic"),
    ("Software", "software-symbolic"),
    ("Monitor", "utilities-system-monitor-symbolic"),
    ("Settings", "preferences-system-symbolic"),
]
PAGES = ["Desktop", "Files", "Settings", "About"]
CONFIG = os.path.expanduser("~/.config/vixzen/preview.json")

def load_config():
    try:
        with open(CONFIG) as f:
            d = json.load(f)
        if d.get("theme") in THEMES and d.get("perf") in ("saver", "balanced", "enhanced", "insane"):
            return d
    except Exception:
        pass
    return {"theme": "dark", "perf": "balanced", "wallpaper": "Indigo Dusk",
            "accent": "Vixzen Indigo"}

def save_config(theme, perf, wallpaper, accent="Vixzen Indigo"):
    try:
        os.makedirs(os.path.dirname(CONFIG), exist_ok=True)
        with open(CONFIG, "w") as f:
            json.dump({"theme": theme, "perf": perf, "wallpaper": wallpaper,
                       "accent": accent}, f)
    except Exception:
        pass

class PreviewWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="VixzenOS Preview")
        cfg = load_config()
        self.set_default_size(1100, 700)
        self.theme, self.perf = cfg["theme"], cfg["perf"]
        self.wallpaper = cfg.get("wallpaper", "Indigo Dusk")
        self.accent = cfg.get("accent", "Vixzen Indigo")
        self.active_apps = set()  # taskbar running indicators (mock)
        # Prefer the custom Vixzen globe for Browser when the icon theme has it.
        global APPS
        try:
            _theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            if _theme is not None and _theme.has_icon("vixzen-browser"):
                APPS = [(n, ("vixzen-browser" if n == "Browser" else i)) for n, i in APPS]
        except Exception:
            pass
        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self.css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.apply_style()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        header = Adw.HeaderBar()
        logo = Gtk.Label(label="◈ VixzenOS  —  Preview v0.2 (mock, safe)")
        logo.set_xalign(0)
        header.set_title_widget(logo)
        self.theme_btn = Gtk.ToggleButton(
            label="☀ Light" if self.theme == "light" else "☾ Dark",
            active=(self.theme == "light"))
        self.theme_btn.connect("toggled", self.on_theme)
        header.pack_end(self.theme_btn)
        self.perf_drop = Gtk.DropDown.new_from_strings(["Saver", "Balanced", "Enhanced", "Insane"])
        self.perf_drop.set_selected(("saver", "balanced", "enhanced", "insane").index(self.perf))
        self.perf_drop.connect("notify::selected", self.on_perf)
        header.pack_end(self.perf_drop)
        notif_btn = Gtk.Button(icon_name="notifications-symbolic", tooltip_text="Notifications")
        notif_btn.connect("clicked", self.show_notifications)
        header.pack_end(notif_btn)
        root.append(header)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        body.set_hexpand(True); body.set_vexpand(True)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(body, f"set_{m}")(12)
        root.append(body)

        self.sidebar = Gtk.ListBox()
        self.sidebar.add_css_class("vix-card")
        self.sidebar.set_size_request(190, -1)
        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True); self.stack.set_vexpand(True)
        for name, icon in [("Desktop", "user-home-symbolic"), ("Files", "folder-symbolic"),
                           ("Settings", "preferences-system-symbolic"), ("About", "help-about-symbolic")]:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(spacing=8)
            box.append(Gtk.Image.new_from_icon_name(icon))
            box.append(Gtk.Label(label=name))
            row.set_child(box)
            self.sidebar.append(row)
        self.sidebar.connect("row-selected", self.on_nav)
        body.append(self.sidebar)
        body.append(self.stack)

        self.build_desktop_page()
        self.build_files_page()
        self.build_settings_page()
        self.build_about_page()
        self.stack.set_visible_child_name("Desktop")
        self.apply_style()  # now stack exists → sets transition duration

        # Taskbar with active indicators + tray mocks
        taskbar = Gtk.Box(spacing=6)
        taskbar.add_css_class("vix-taskbar")
        launcher = Gtk.Button(label="◈ Vixzen", tooltip_text="Super — open launcher")
        launcher.add_css_class("vix-accent")
        launcher.connect("clicked", self.show_launcher)
        taskbar.append(launcher)
        self.task_btns = {}
        for name, icon in APPS:
            b = Gtk.ToggleButton(icon_name=icon, tooltip_text=f"{name} (press 1-6)")
            b.connect("toggled", self.on_task_toggle, name)
            taskbar.append(b)
            self.task_btns[name] = b
        spacer = Gtk.Box(); spacer.set_hexpand(True)
        taskbar.append(spacer)
        for icon, tip in [("network-wireless-symbolic", "Network (mock)"),
                          ("audio-volume-high-symbolic", "Audio (mock)"),
                          ("battery-good-symbolic", "Battery (mock)")]:
            t = Gtk.Button(icon_name=icon, tooltip_text=tip)
            t.connect("clicked", lambda _b, n=tip: self.toast(n))
            taskbar.append(t)
        self.perf_label = Gtk.Label(label=self.perf.capitalize())
        taskbar.append(self.perf_label)
        self.clock = Gtk.Label()
        taskbar.append(self.clock)
        root.append(taskbar)
        GLib.timeout_add_seconds(1, self.tick)
        self.tick()
        self.add_shortcuts()
        if self.perf == "insane":
            self.show_intro()

    # ---- styling / state ----
    def apply_style(self):
        self.css.load_from_data((css_for(self.theme, self.perf, self.wallpaper,
                                        self.accent) + LIQUID_CARD).encode())
        if getattr(self, "stack", None) is not None:
            self.stack.set_transition_duration(
                {"saver": 0, "balanced": 150, "enhanced": 220,
                 "insane": 600}[self.perf])
            if self.perf in ("enhanced", "insane"):
                self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            elif self.perf == "balanced":
                self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            else:
                self.stack.set_transition_type(Gtk.StackTransitionType.NONE)
        save_config(self.theme, self.perf, self.wallpaper, self.accent)

    def on_theme(self, btn):
        self.theme = "light" if btn.get_active() else "dark"
        btn.set_label("☀ Light" if self.theme == "light" else "☾ Dark")
        self.apply_style()

    def on_perf(self, drop, _pspec):
        self.perf = ("saver", "balanced", "enhanced", "insane")[drop.get_selected()]
        self.perf_label.set_label(self.perf.capitalize())
        self.apply_style()

    def tick(self):
        self.clock.set_label(datetime.datetime.now().strftime("%H:%M  %Y-%m-%d"))
        return True

    def show_intro(self):
        """Cinematic loading screen (insane mode only): logo, spinner,
        pulsing progress bar. Auto-dismisses after ~2 s. Mock only."""
        dlg = Gtk.Window(transient_for=self, modal=True, decorated=False,
                         resizable=False)
        dlg.set_default_size(440, 280)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(box, f"set_{m}")(28)
        logo = Gtk.Label()
        logo.set_markup("<span size='48000' weight='bold'>◈</span>")
        box.append(logo)
        title = Gtk.Label()
        title.set_markup("<span size='x-large' weight='bold'>VixzenOS</span>\n"
                         "<span>Lightweight • Graphical • Yours</span>")
        title.set_justify(Gtk.Justification.CENTER)
        box.append(title)
        spin = Gtk.Spinner(spinning=True)
        spin.set_size_request(32, 32)
        box.append(spin)
        bar = Gtk.ProgressBar()
        box.append(bar)
        dlg.set_child(box)
        dlg.present()

        def pulse():
            if not dlg.get_visible():
                return False
            bar.pulse()
            return True

        def dismiss():
            try:
                dlg.close()
            except Exception:
                pass
            return False

        GLib.timeout_add(100, pulse)
        GLib.timeout_add_seconds(2, dismiss)

    def on_nav(self, _box, row):
        if row:
            self.stack.set_visible_child_name(
                row.get_child().get_last_child().get_label())

    def on_task_toggle(self, btn, name):
        if btn.get_active():
            self.active_apps.add(name)
            btn.add_css_class("vix-active")
            self.open_mock(name, keep_active=True)
        else:
            self.active_apps.discard(name)
            btn.remove_css_class("vix-active")

    def add_shortcuts(self):
        ctl = Gtk.ShortcutController.new()
        ctl.set_scope(Gtk.ShortcutScope.GLOBAL)
        self.add_controller(ctl)
        ctl.add_shortcut(Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("Super_L"),
            Gtk.CallbackAction.new(lambda *_: (self.show_launcher(None), True)[1])))
        for i, page in enumerate(PAGES, start=1):
            ctl.add_shortcut(Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(f"<Alt>{i}"),
                Gtk.CallbackAction.new(
                    lambda *_, p=page: (self.stack.set_visible_child_name(p), True)[1])))
        for i, (name, _) in enumerate(APPS, start=1):
            ctl.add_shortcut(Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(f"{i}"),
                Gtk.CallbackAction.new(
                    lambda *_, n=name: (self.task_btns[n].set_active(
                        not self.task_btns[n].get_active()), True)[1])))

    # ---- pages ----
    def build_desktop_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        hero = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        hero.add_css_class("vix-hero")
        hero.set_margin_top(12)
        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>◈ VixzenOS</span>\nLightweight • Graphical • Yours")
        hero.append(title)
        hero.append(Gtk.Label(label=f"Wallpaper: {self.wallpaper} — pick below (preview only)"))
        box.append(hero)
        wp_row = Gtk.Box(spacing=6)
        for w in WALLPAPERS:
            b = Gtk.Button(label=w)
            b.connect("clicked", lambda _b, ww=w: self.set_wallpaper(ww))
            wp_row.append(b)
        box.append(wp_row)
        grid = Gtk.Grid(column_spacing=12, row_spacing=12)
        for i, (name, icon) in enumerate(APPS):
            b = Gtk.Button()
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.append(Gtk.Image.new_from_icon_name(icon))
            inner.append(Gtk.Label(label=name))
            b.set_child(inner)
            b.connect("clicked", lambda _b, n=name: self.task_btns[n].set_active(True))
            grid.attach(b, i % 3, i // 3, 1, 1)
        box.append(grid)
        self.stack.add_titled(box, "Desktop", "Desktop")

    def set_wallpaper(self, w):
        self.wallpaper = w
        self.apply_style()
        self.toast(f"Wallpaper: {w}")

    def build_files_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        places = Gtk.ListBox()
        places.add_css_class("vix-card")
        places.set_size_request(150, -1)
        for p in ("Home", "Desktop", "Documents", "Downloads", "Pictures", "Trash"):
            places.append(Gtk.Label(label=p))
        box.append(places)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.set_hexpand(True); right.set_vexpand(True)
        self.crumb = Gtk.Label(label="~/  •  read-only mock", xalign=0)
        right.append(self.crumb)
        self.search = Gtk.SearchEntry(placeholder_text="Filter (mock, read-only)…")
        self.search.connect("search-changed", lambda *_: self.refresh_files())
        right.append(self.search)
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        self.flist = Gtk.ListBox()
        scroll.set_child(self.flist)
        right.append(scroll)
        box.append(right)
        self.stack.add_titled(box, "Files", "Files")
        self.refresh_files()

    def refresh_files(self):
        while (row := self.flist.get_row_at_index(0)):
            self.flist.remove(row)
        q = self.search.get_text().lower() if hasattr(self, "search") else ""
        home = os.path.expanduser("~")
        try:
            items = sorted(os.listdir(home))[:60]
        except Exception as e:
            items = [f"(unreadable: {e})"]
        shown = 0
        for it in items:
            if q and q not in it.lower():
                continue
            prefix = "📁 " if os.path.isdir(os.path.join(home, it)) else "📄 "
            self.flist.append(Gtk.Label(label=prefix + it, xalign=0))
            shown += 1
        self.flist.append(Gtk.Label(
            label=f"({shown} shown, capped at 60 — mock, read-only)", xalign=0))

    def build_settings_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(Gtk.Label(label="Appearance (preview only, saved to ~/.config/vixzen/)"))
        box.append(Gtk.Label(label="Brand accent — recolors taskbar launcher, buttons, highlights:"))
        accents = Gtk.Box(spacing=6)
        for a in ACCENTS:
            b = Gtk.Button(label=a)
            b.connect("clicked", lambda _b, aa=a: self.set_accent(aa))
            accents.append(b)
        box.append(accents)
        self.accent_label = Gtk.Label(label=f"Accent: {self.accent}")
        box.append(self.accent_label)
        modes = Gtk.Box(spacing=6)
        for m in ("saver", "balanced", "enhanced", "insane"):
            b = Gtk.Button(label=m.capitalize())
            b.connect("clicked", lambda _b, mm=m: self.perf_drop.set_selected(
                ("saver", "balanced", "enhanced", "insane").index(mm)))
            modes.append(b)
        box.append(modes)
        box.append(Gtk.Label(label="Shortcuts: Super=launcher • Alt+1..4=pages • 1..6=apps"))
        self.stack.add_titled(box, "Settings", "Settings")

    def set_accent(self, a):
        self.accent = a
        self.accent_label.set_label(f"Accent: {a}")
        self.apply_style()
        self.toast(f"Vixzen accent: {a} (saved)")

    def build_about_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.append(Gtk.Label(label="VixzenOS Preview 0.2 — mock interface.\nReal window management + ISO in Milestones 3–5.\nNo user files are modified; only ~/.config/vixzen/preview.json stores theme choices."))
        self.stack.add_titled(box, "About", "About")

    # ---- dialogs ----
    def toast(self, msg):
        dlg = Adw.MessageDialog.new(self, "VixzenOS")
        dlg.set_body(msg)
        dlg.add_response("ok", "OK")
        dlg.present()

    def open_mock(self, name, keep_active=False):
        if not keep_active and name in self.task_btns:
            self.task_btns[name].set_active(True)
            return
        dlg = Adw.MessageDialog.new(self, f"{name} (mock)")
        dlg.set_body(f"Preview placeholder for {name}.\nClose it and the taskbar untoggles (like minimize).")
        dlg.add_response("ok", "OK")
        dlg.connect("response", lambda *_: self.task_btns[name].set_active(False))
        dlg.present()

    def show_launcher(self, _b):
        dlg = Adw.MessageDialog.new(self, "◈ Vixzen Launcher (mock)")
        dlg.set_body("Pinned: " + ", ".join(n for n, _ in APPS) + "\nSuper reopens me. Search + workspaces arrive in Milestone 3.")
        dlg.add_response("ok", "Close")
        dlg.present()

    def show_notifications(self, _b):
        dlg = Adw.MessageDialog.new(self, "Notifications (mock)")
        dlg.set_body("No new notifications.\nCalendar + quick settings arrive in Milestone 3.")
        dlg.add_response("ok", "Close")
        dlg.present()

class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
    def do_activate(self):
        PreviewWindow(self).present()

if __name__ == "__main__":
    if "--smoke" in sys.argv:
        import design
        assert set(design.THEMES) == {"light", "dark"}
        assert design.css_for("dark", "saver", "Deep Night")
        assert "600ms" in design.css_for("dark", "insane", "Deep Night")
        assert set(design.PERF_MODES) == {"saver", "balanced", "enhanced", "insane"}
        assert len(WALLPAPERS) >= 2
        print("smoke OK: design tokens + CSS + wallpapers render")
    else:
        App().run(sys.argv)
