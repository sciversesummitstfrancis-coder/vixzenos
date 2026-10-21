#!/usr/bin/env python3
"""Vixzen Web v1.1 — motion browser for VixzenOS.
Run: python3 apps/web-browser/vixzen_web.py [url] [--smoke]
     or (after install): vixzen-web [url]

Layout (Chrome on top, Opera on the side):
- Top: tab strip (Adw.TabBar, Chrome-style) + tab overview button
- Toolbar: back/forward/reload/home, omnibox-style address bar, lock, star,
  new-tab, profile avatar, main menu
- No sidebar: pure Google-style top chrome (tabs, toolbar, bookmark bar)
- Home: Opera-style speed-dial (bookmark tiles + frequent sites + search)
- Native install: `scripts/install-web.sh` (~/.local) or RPM
  `packaging/vixzen-web.spec`, launcher `vixzen-web`, icon
  `assets/branding/vixzen-web.svg`, .desktop `os.vixzen.web.desktop`.
"""
import os
import sys
import json
import html as htmlmod
import urllib.parse

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
try:
    gi.require_version("WebKit", "6.0")
    from gi.repository import WebKit as WK
    WK_API = 6
except Exception:
    gi.require_version("WebKit2", "4.1")
    from gi.repository import WebKit2 as WK
    WK_API = 4
from gi.repository import Gtk, Adw, Gio, GLib, Gdk, Pango

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "preview", "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from design import css_for, LIQUID_CARD, LIQUID_GLASS, CHROME_SKIN, INSANE_MOTION
try:
    import vixzen_search as VSearch
except Exception:
    VSearch = None
try:
    import blocklist as BL
except Exception:
    BL = None
try:
    import chrome_import as CImport
except Exception:
    CImport = None

APP_ID = "os.vixzen.web"
VERSION = "1.1"
from web_core import (HOME_URL, CONFIG_DIR, BOOKMARKS_FILE, HISTORY_FILE,
    SETTINGS_FILE, HISTORY_MAX, SPEED_DIAL_MAX, CLOSED_MAX, SEARCH_ENGINES,
    DEFAULT_SETTINGS, load_settings, save_settings, search_url, fetch_suggestions,
    ensure_config, load_json, save_json, to_url, start_page_html)
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")


def tune_process_cache():
    """Shared web-process cache: DOCUMENT_BROWSER balances speed vs 8GB RAM."""
    try:
        ctx = WK.WebContext.get_default()
        if hasattr(ctx, "set_cache_model") and hasattr(WK, "CacheModel"):
            ctx.set_cache_model(WK.CacheModel.DOCUMENT_BROWSER)
    except Exception:
        pass



def make_webview():
    settings = WK.Settings(
        enable_developer_extras=True,
        enable_media_stream=False,
        enable_webaudio=True,
        enable_webgl=True,
        enable_smooth_scrolling=True,
        enable_page_cache=True,          # bfcache: back/forward feels instant
        enable_2d_canvas_acceleration=True,
        default_font_size=16,
    )
    try:
        if hasattr(WK, "HardwareAccelerationPolicy"):
            settings.set_hardware_acceleration_policy(WK.HardwareAccelerationPolicy.ALWAYS)
    except Exception:
        pass
    if WK_API == 4:
        ctx = WK.WebContext.get_default()
        if hasattr(ctx, "set_process_model"):
            try:
                ctx.set_process_model(WK.ProcessModel.MULTIPLE_SECONDARY_PROCESSES)
            except Exception:
                pass
    if hasattr(WK.WebView, "new_with_settings"):
        return WK.WebView.new_with_settings(settings)
    view = WK.WebView()
    try:
        view.set_settings(settings)
    except Exception:
        pass
    return view


class BrowserWin(Adw.ApplicationWindow):
    def __init__(self, app, start_url):
        super().__init__(application=app, title="Vixzen Web")
        self.set_default_size(1150, 730)
        ensure_config()
        self.bookmarks = load_json(BOOKMARKS_FILE, [])
        self.history = load_json(HISTORY_FILE, [])
        self.settings = load_settings()
        self.settings.setdefault("allowed_sites", [])
        self.allowed_sites = set(self.settings.get("allowed_sites", []))
        self.block_enabled = bool(self.settings.get("blocking", True))
        self.blocked_hosts = BL.get_hosts() if BL is not None else set()
        self._ucf = None
        self.closed_stack = []
        self._suggest_token = 0
        self._suggest_pending = None

        self._css = None
        self._col = None
        self.apply_skin()

        # Google-style: one clean column, no sidebar. Everything lives in
        # the tab strip, toolbar, bookmark bar, or the ⋮ menu.
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.add_css_class("glass-shell")
        self._col = col
        _edge = 0 if self.skin() == "chrome" else 8
        col.set_spacing(_edge)
        for _m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
            getattr(col, f"set_{_m}")(_edge)
        self.set_content(col)

        # --- Chrome-style: tab strip on top ---
        tabrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tabrow.add_css_class("glass-tabstrip")
        for m in ("margin_start", "margin_end"):
            getattr(tabrow, f"set_{m}")(2)
        tabrow.set_margin_top(2)
        self.tabbar = Adw.TabBar(autohide=False, expand_tabs=True)
        self.tabbar.set_hexpand(True)
        tabrow.append(self.tabbar)
        self.overview_btn = Gtk.Button(icon_name="view-grid-symbolic", tooltip_text="All tabs (Ctrl+Shift+A)")
        self.overview_btn.connect("clicked", lambda *_: self.show_tabs_overview())
        tabrow.append(self.overview_btn)
        col.append(tabrow)

        # --- toolbar / omnibox (floating glass) ---
        hb = Adw.HeaderBar()
        hb.add_css_class("glass-bar")
        self.back_btn = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Back (Alt+Left)")
        self.back_btn.connect("clicked", lambda *_: self.current_view() and self.current_view().go_back())
        hb.pack_start(self.back_btn)
        self.fwd_btn = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Forward (Alt+Right)")
        self.fwd_btn.connect("clicked", lambda *_: self.current_view() and self.current_view().go_forward())
        hb.pack_start(self.fwd_btn)
        self.reload_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Reload (Ctrl+R)")
        self.reload_btn.connect("clicked", lambda *_: self.current_view() and self.current_view().reload())
        hb.pack_start(self.reload_btn)
        self.home_btn = Gtk.Button(icon_name="go-home-symbolic", tooltip_text="Home (Alt+Home)")
        self.home_btn.connect("clicked", lambda *_: self.load_in_current(HOME_URL))
        hb.pack_start(self.home_btn)

        self.url = Gtk.Entry(placeholder_text="Search or enter address…  (Ctrl+L)")
        self.url.add_css_class("glass-omnibox")
        self.url.set_hexpand(True)
        self.url.connect("activate", self.on_url_enter)
        hb.set_title_widget(self.url)

        self.star = Gtk.Button(icon_name="non-starred-symbolic", tooltip_text="Bookmark (Ctrl+D)")
        self.star.connect("clicked", self.on_bookmark)
        hb.pack_end(self.star)
        self.shield = Gtk.Button(label="🛡", tooltip_text="Tracker blocking: on")
        self.shield.connect("clicked", lambda *_: self.toggle_site_block())
        hb.pack_end(self.shield)
        # profile avatar (Chrome-style identity, local only)
        profile = Gtk.MenuButton(icon_name="avatar-default-symbolic", tooltip_text="Profile — local only")
        profile.add_css_class("chrome-avatar")
        pmenu = Gio.Menu()
        pmenu.append("About Vixzen Web", "win.about")
        profile.set_menu_model(pmenu)
        hb.pack_end(profile)

        self.new_tab_btn = Gtk.Button(icon_name="tab-new-symbolic", tooltip_text="New tab (Ctrl+T)")
        self.new_tab_btn.connect("clicked", lambda *_: self.new_tab(HOME_URL))
        hb.pack_end(self.new_tab_btn)

        menu = Gio.Menu()
        menu.append("New tab (Ctrl+T)", "win.new-tab")
        menu.append("Home (Alt+Home)", "win.go-home")
        menu.append("All tabs… (Ctrl+Shift+A)", "win.tabs-overview")
        menu.append("Find in page… (Ctrl+F)", "win.find")
        menu.append("Zoom in (Ctrl++)", "win.zoom-in")
        menu.append("Zoom out (Ctrl+-)", "win.zoom-out")
        menu.append("Reset zoom (Ctrl+0)", "win.zoom-reset")
        menu.append("Effects: Balanced/Insane", "win.toggle-fx")
        menu.append("Settings (Ctrl+,)", "win.show-settings")
        menu.append("History (Ctrl+H)", "win.show-history-page")
        menu.append("Bookmarks (Ctrl+Shift+O)", "win.show-bookmarks-page")
        menu.append("Import from Chrome/Firefox…", "win.do-import")
        menu.append("Clear history + cache… (Ctrl+Shift+Del)", "win.clear-data")
        menu.append("Inspect page (Ctrl+Shift+I)", "win.inspect-page")
        menu.append("Block trackers on this site (on/off)", "win.toggle-site-block")
        menu.append("Bookmark bar (Ctrl+Shift+B)", "win.toggle-bar")
        menu.append("Reopen closed tab (Ctrl+Shift+T)", "win.reopen-closed")
        menu.append("Duplicate tab", "win.duplicate-tab")
        menu.append("Search engine…", "win.search-engine")
        menu.append("About Vixzen Web", "win.about")
        hb.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu))
        col.append(hb)

        # --- Chrome-style bookmark bar (Ctrl+Shift+B) ---
        self.bm_scroll = Gtk.ScrolledWindow()
        self.bm_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.bm_scroll.set_propagate_natural_height(True)
        self.bm_scroll.set_max_content_height(36)
        self.bm_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        for m in ("margin_start", "margin_end"):
            getattr(self.bm_bar, f"set_{m}")(8)
        self.bm_scroll.set_child(self.bm_bar)
        col.append(self.bm_scroll)
        self.refresh_bookmark_bar()
        self._apply_bar_visibility()

        # --- Omnibox search suggestions (popover) ---
        self.suggest_pop = Gtk.Popover()
        self.suggest_pop.set_parent(self.url)
        self.suggest_pop.set_autohide(True)
        self.suggest_box = Gtk.ListBox()
        self.suggest_box.connect("row-activated", self._on_suggest_pick)
        self.suggest_pop.set_child(self.suggest_box)
        self.url.connect("changed", self._on_url_typed)

        self.progress = Gtk.ProgressBar(show_text=False)
        self.progress.set_fraction(0.0)
        col.append(self.progress)

        self.tabs = Adw.TabView()
        self.tabs.add_css_class("glass-view")
        self.tabbar.set_view(self.tabs)
        self.tabs.connect("page-attached", lambda *_: self.refresh_chrome())
        self.tabs.connect("page-detached", lambda *_: self.refresh_chrome())
        self.tabs.connect("notify::selected-page", lambda *args: self.refresh_chrome())
        try:
            self.tabs.connect("close-page", self.on_tab_closing)
        except Exception:
            pass
        tab_rc = Gtk.GestureClick.new()
        tab_rc.set_button(3)
        tab_rc.connect("pressed", self.on_tabbar_right_click)
        self.tabbar.add_controller(tab_rc)
        col.append(self.tabs)
        self.tabs.set_vexpand(True)

        self.findbar = Gtk.Box(spacing=6, visible=False)
        for m in ("margin_start", "margin_end", "margin_top", "margin_bottom"):
            getattr(self.findbar, f"set_{m}")(6)
        self.find_entry = Gtk.SearchEntry(placeholder_text="Find in page…")
        self.find_entry.set_hexpand(True)
        self.find_entry.connect("search-changed", self.on_find_changed)
        self.find_entry.connect("activate", lambda *_: self.find_next())
        self.findbar.append(self.find_entry)
        fn = Gtk.Button(icon_name="go-down-symbolic", tooltip_text="Next (Enter)")
        fn.connect("clicked", lambda *_: self.find_next())
        self.findbar.append(fn)
        fp = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Previous")
        fp.connect("clicked", lambda *_: self.find_prev())
        self.findbar.append(fp)
        fc = Gtk.Button(icon_name="window-close-symbolic", tooltip_text="Close (Esc)")
        fc.connect("clicked", lambda *_: self.findbar.hide())
        self.findbar.append(fc)
        col.append(self.findbar)

        self.status = Gtk.Label(label=f"◈ Vixzen Web v{VERSION} · Liquid Glass", xalign=0)
        self.status.add_css_class("glass-pill")
        self.status.set_margin_start(10)
        self.status.set_margin_bottom(4)
        col.append(self.status)

        for name, cb in (("new-tab", lambda *_: self.new_tab(HOME_URL)),
                         ("go-home", lambda *_: self.load_in_current(HOME_URL)),
                         ("find", lambda *_: self.findbar.show() or self.find_entry.grab_focus()),
                         ("zoom-in", lambda *_: self.zoom(0.1)),
                         ("zoom-out", lambda *_: self.zoom(-0.1)),
                         ("zoom-reset", lambda *_: self.zoom_reset()),
                         ("show-bookmarks", lambda *_: self.load_in_current("vixzen:bookmarks")),
                         ("show-history", lambda *_: self.load_in_current("vixzen:history")),
                         ("show-bookmarks-page", lambda *_: self.load_in_current("vixzen:bookmarks")),
                         ("show-history-page", lambda *_: self.load_in_current("vixzen:history")),
                         ("show-settings", lambda *_: self.load_in_current("vixzen:settings")),
                         ("do-import", lambda *_: self.do_import()),
                         ("clear-data", lambda *_: (self.clear_data(), self.load_in_current("vixzen:settings"))),
                         ("inspect-page", lambda *_: self.inspect_page()),
                         ("tabs-overview", lambda *_: self.show_tabs_overview()),
                         ("toggle-bar", lambda *_: self.toggle_bar()),
                         ("toggle-site-block", lambda *_: self.toggle_site_block()),
                         ("toggle-fx", lambda *_: self.apply_effects()),
                         ("reopen-closed", lambda *_: self.reopen_closed()),
                         ("duplicate-tab", lambda *_: self.duplicate_tab()),
                         ("pin-tab", lambda *_: self.toggle_pin()),
                         ("close-others", lambda *_: self.close_others()),
                         ("search-engine", lambda *_: self.show_search_engine()),
                         ("about", lambda *_: self.show_about())):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", cb)
            self.add_action(act)

        self._chrome_us = {}
        self._history_timer = None
        self.add_shortcuts()
        tune_process_cache()
        # Heavy WebView builds AFTER the frame paints (idle), so the window
        # appears instantly even on HD 520.
        GLib.idle_add(self._first_tab, start_url or HOME_URL)
        GLib.idle_add(self._init_blocklist)
        try:
            self.connect("close-request", self._on_close_save_session)
        except Exception:
            pass
        if not self.settings.get("welcomed", False):
            GLib.idle_add(self.show_welcome)

    def _first_tab(self, url):
        try:
            if self.tabs.get_n_pages() == 0:
                self.new_tab(url)
        except Exception:
            pass
        return False

    def skin(self):
        return self.settings.get("appearance", "chrome")

    def fx(self):
        return self.settings.get("effects", "balanced") if self.settings.get("effects") in ("balanced", "insane") else "balanced"

    def apply_effects(self):
        self.settings["effects"] = "insane" if self.fx() == "balanced" else "balanced"
        save_settings(self.settings)
        self.apply_skin()
        self.status.set_label(f"◈ Effects: {self.fx()}")

    def apply_skin(self):
        """Hot-swap Chrome <-> Vixzen glass. Same widgets, different skin."""
        skin = self.skin()
        try:
            disp = Gdk.Display.get_default()
            if self._css is not None:
                try:
                    Gtk.StyleContext.remove_provider_for_display(disp, self._css)
                except Exception:
                    pass
            fx = self.fx()
            base = css_for("light" if skin == "chrome" else "dark", fx)
            extra = CHROME_SKIN if skin == "chrome" else LIQUID_GLASS
            if fx == "insane":
                extra += INSANE_MOTION
            self._css = Gtk.CssProvider()
            self._css.load_from_data((base + LIQUID_CARD + extra).encode())
            Gtk.StyleContext.add_provider_for_display(
                disp, self._css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            try:
                Adw.StyleManager.get_default().set_color_scheme(
                    Adw.ColorScheme.FORCE_LIGHT if skin == "chrome"
                    else Adw.ColorScheme.DEFAULT)
            except Exception:
                pass
            if self._col is not None:
                edge = 0 if skin == "chrome" else 8
                self._col.set_spacing(edge)
                for m in ("margin_top", "margin_bottom", "margin_start", "margin_end"):
                    getattr(self._col, f"set_{m}")(edge)
        except Exception:
            pass
        try:
            for v in self.views():
                try:
                    if (v.get_uri() or "") in (HOME_URL, "vixzen:home", ""):
                        self.load_in_view(v, HOME_URL)
                except Exception:
                    pass
        except Exception:
            pass  # tabs may not exist yet during __init__

    # ---- tabs / views ----
    def new_tab(self, url):
        view = make_webview()
        view.connect("load-changed", self.on_load_changed)
        view.connect("notify::estimated-load-progress", self.on_progress)
        view.connect("notify::uri", lambda *args: self.refresh_chrome())
        view.connect("notify::title", self.on_title)
        view.connect("decide-policy", self.on_decide_policy)
        if WK_API == 6:
            view.connect("load-failed", self.on_load_failed)
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(view)
        try:
            if self._ucf is not None and self.block_enabled:
                view.get_user_content_manager().add_filter(self._ucf)
        except Exception:
            pass
        page = self.tabs.append(scroll)
        view._tab_page = page
        self.tabs.set_selected_page(page)
        self.load_in_view(view, url)
        return view

    def _view_for_page(self, page):
        if page is None:
            return None
        node = page.get_child()
        for _ in range(4):
            if node is None:
                return None
            if isinstance(node, WK.WebView):
                return node
            try:
                node = node.get_child()
            except Exception:
                return None
        return None

    def views(self):
        out = []
        for i in range(self.tabs.get_n_pages()):
            v = self._view_for_page(self.tabs.get_nth_page(i))
            if v is not None:
                out.append(v)
        return out

    def current_view(self):
        return self._view_for_page(self.tabs.get_selected_page())

    def load_in_view(self, view, url):
        if url == HOME_URL:
            view.load_alternate_html(start_page_html(self.bookmarks, self.history, self.skin(), self.fx()), HOME_URL, None)
            self.url.set_text("")
            self.status.set_label("◈ New tab")
        elif url.startswith("vixzen:"):
            self.render_local(view, url)
        else:
            view.load_uri(url)

    def render_local(self, view, url):
        base = url.split("?", 1)[0]
        if base == "vixzen:search" and VSearch is not None:
            self.render_vixzen_search(view, url)
        elif base == "vixzen:settings":
            self.apply_settings_act(url)
            view.load_alternate_html(self.settings_page_html(url), "vixzen:settings", None)
            self.url.set_text("")
            self.status.set_label("◈ Settings")
        elif base == "vixzen:history":
            if self.apply_history_act(url):
                url = "vixzen:history"
            view.load_alternate_html(self.history_page_html(url), "vixzen:history", None)
            self.url.set_text("")
            self.status.set_label("◈ History")
        elif base == "vixzen:bookmarks":
            if self.apply_bookmarks_act(url):
                url = "vixzen:bookmarks"
            view.load_alternate_html(self.bookmarks_page_html(url), "vixzen:bookmarks", None)
            self.url.set_text("")
            self.status.set_label("◈ Bookmarks")
        else:
            self.load_in_view(view, HOME_URL)

    # ---- chrome:// pages (local, glass, working links) ----
    def _page_shell(self, title, body):
        nav = ("<div class='nav'><a href='vixzen:home'>New tab</a>"
               "<a href='vixzen:settings'>Settings</a>"
               "<a href='vixzen:history'>History</a>"
               "<a href='vixzen:bookmarks'>Bookmarks</a></div>")
        return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{htmlmod.escape(title)} — Vixzen Web</title>
<style>
body{{font-family:-apple-system,Cantarell,system-ui,sans-serif;margin:0;min-height:100vh;color:#fff;
background:radial-gradient(900px 500px at 50% 0%,rgba(79,70,229,.45),transparent 60%),
linear-gradient(180deg,#171a30,#0b0e1a);}}
.wrap{{max-width:680px;margin:0 auto;padding:40px 18px 60px}}
.nav{{display:flex;gap:14px;margin-bottom:20px;font-size:14px}}.nav a{{color:#a5b4ff;text-decoration:none}}
.card{{padding:18px;border-radius:18px;margin:12px 0;background:rgba(255,255,255,.09);
-webkit-backdrop-filter:blur(20px);backdrop-filter:blur(20px);
border:1px solid rgba(255,255,255,.2);border-top-color:rgba(255,255,255,.45);
box-shadow:inset 0 1px 0 rgba(255,255,255,.25)}}
h1{{font-size:24px;margin:0 0 4px}}h2{{font-size:16px;margin:0 0 8px}}.sub{{opacity:.65;font-size:13px}}
a.btn{{display:inline-block;margin:4px 6px 4px 0;padding:8px 16px;border-radius:999px;text-decoration:none;
color:#fff;background:rgba(124,124,255,.35);border:1px solid rgba(255,255,255,.3);
border-top-color:rgba(255,255,255,.55)}}
a.btn.off{{background:rgba(255,255,255,.08)}}
.row{{display:flex;gap:8px;align-items:center;margin:6px 0;flex-wrap:wrap}}
input[type=text]{{flex:1;min-width:200px;padding:9px 14px;border-radius:999px;border:1px solid rgba(255,255,255,.25);
background:rgba(0,0,0,.28);color:#fff;font-size:14px;outline:0}}
.item{{padding:8px 2px;border-bottom:1px solid rgba(255,255,255,.08);font-size:14px}}
.item a.t{{color:#fff;text-decoration:none}}.item .u{{opacity:.55;font-size:12px}}
.item a.x{{color:#ff9d9d;text-decoration:none;margin-left:10px}}</style></head>
<body><div class="wrap">{nav}{body}</div></body></html>"""

    def _q(self, url):
        try:
            return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        except Exception:
            return {}

    def settings_page_html(self, _url=""):
        eng = self.settings.get("engine", "vixzen")
        sk = self.settings.get("appearance", "chrome")
        fx = self.settings.get("effects", "balanced")
        eng_btns = "".join(
            f"<a class='btn{"" if k == eng else " off"}' href='vixzen:settings?act=engine&arg={k}'>{s['name']}</a>"
            for k, s in SEARCH_ENGINES.items())
        bar = self.settings.get("bookmark_bar", True)
        blk = self.block_enabled
        stu = self.settings.get("startup", "newtab")
        n_hosts = len(self.blocked_hosts) if BL else 0
        return self._page_shell("Settings", f"""
<h1>Settings</h1><div class='sub'>Everything here applies instantly.</div>
<div class='card'><h2>Search engine</h2>{eng_btns}</div>
<div class='card'><h2>On startup</h2>
<a class='btn{" " if stu == "newtab" else " off"}' href='vixzen:settings?act=startup&arg=newtab'>Open a new tab</a>
<a class='btn{" " if stu == "restore" else " off"}' href='vixzen:settings?act=startup&arg=restore'>Restore last session</a></div>
<div class='card'><h2>Appearance</h2>
<div class='sub'>Motion is opt-in; Balanced never animates forever.</div>
<a class='btn{" " if sk == "chrome" else " off"}' href='vixzen:settings?act=skin&arg=chrome'>Chrome look</a>
<a class='btn{" " if sk == "glass" else " off"}' href='vixzen:settings?act=skin&arg=glass'>Vixzen glass</a><br>
<div class='row' style='margin-top:8px'>
<a class='btn{" " if fx == "balanced" else " off"}' href='vixzen:settings?act=fx&arg=balanced'>Balanced motion</a>
<a class='btn{" " if fx == "insane" else " off"}' href='vixzen:settings?act=fx&arg=insane'>Insane motion</a></div>
<a class='btn{" " if bar else " off"}' href='vixzen:settings?act=bar'>Bookmark bar: {"on" if bar else "off"}</a></div>
<div class='card'><h2>Privacy</h2><div class='sub'>{n_hosts} tracker hosts on the list.</div>
<a class='btn{" " if blk else " off"}' href='vixzen:settings?act=block'>Tracker blocking: {"on" if blk else "off"}</a>
<a class='btn off' href='vixzen:settings?act=clear'>Clear history + cache…</a></div>
<div class='card'><h2>Bring your stuff</h2>
<a class='btn off' href='vixzen:settings?act=import'>Import from Chrome / Firefox…</a></div>
<div class='card'><h2>About</h2><div class='sub'>Vixzen Web v{VERSION} · WebKitGTK · private by default.</div></div>""")

    def apply_settings_act(self, url):
        q = self._q(url)
        act = (q.get("act") or [""])[0]
        arg = (q.get("arg") or [""])[0]
        if act == "engine" and arg in SEARCH_ENGINES:
            self.settings["engine"] = arg
        elif act == "bar":
            self.settings["bookmark_bar"] = not self.settings.get("bookmark_bar", True)
            self._apply_bar_visibility()
        elif act == "block":
            self.settings["blocking"] = not self.settings.get("blocking", True)
            self.block_enabled = bool(self.settings["blocking"])
            self._init_blocklist()
        elif act == "skin" and arg in ("chrome", "glass"):
            self.settings["appearance"] = arg
            self.apply_skin()
        elif act == "fx" and arg in ("balanced", "insane"):
            self.settings["effects"] = arg
            self.apply_skin()
        elif act == "startup" and arg in ("newtab", "restore"):
            self.settings["startup"] = arg
        elif act == "clear":
            self.clear_data()
            self.status.set_label("◈ History and cache cleared")
        elif act == "import":
            self.do_import()
        else:
            return
        save_settings(self.settings)
        self.refresh_chrome()

    def history_page_html(self, url):
        q = (self._q(url).get("q") or [""])[0].lower()
        items = [h for h in reversed(self.history)
                 if not q or q in f"{h.get('title', '')} {h.get('url', '')}".lower()][:100]
        rows = "".join(
            f"<div class='item'><a class='t' href='{htmlmod.escape(h.get('url', ''))}'>"
            f"{htmlmod.escape(h.get('title', '')[:70])}</a>"
            f"<div class='u'>{htmlmod.escape(h.get('url', '')[:90])}</div></div>"
            for h in items) or "<div class='sub'>Nothing here yet — go browse something.</div>"
        return self._page_shell("History", f"""
<h1>History</h1>
<div class='row'><form action='vixzen:history' style='display:flex;gap:8px;flex:1'>
<input type='text' name='q' value='{htmlmod.escape((self._q(url).get('q') or [''])[0])}' placeholder='Search history…'></form>
<a class='btn off' href='vixzen:history?clear=1'>Clear all…</a></div>
{rows}""")

    def apply_history_act(self, url):
        if (self._q(url).get("clear") or [""])[0] == "1":
            self.history = []
            save_json(HISTORY_FILE, self.history)
            return True
        return False

    def bookmarks_page_html(self, url):
        q = (self._q(url).get("q") or [""])[0].lower()
        items = [(i, b) for i, b in enumerate(self.bookmarks)
                 if not q or q in f"{b.get('title', '')} {b.get('url', '')}".lower()]
        rows = "".join(
            f"<div class='item'><a class='t' href='{htmlmod.escape(b.get('url', ''))}'>"
            f"{htmlmod.escape(b.get('title', '')[:70])}</a>"
            f"<a class='x' href='vixzen:bookmarks?del={urllib.parse.quote_plus(b.get('url', ''))}'>remove</a>"
            f"<div class='u'>{htmlmod.escape(b.get('url', '')[:90])}</div></div>"
            for _i, b in items) or "<div class='sub'>No bookmarks yet — press Ctrl+D on any page.</div>"
        return self._page_shell("Bookmarks", f"""
<h1>Bookmarks</h1>
<div class='row'><form action='vixzen:bookmarks' style='display:flex;gap:8px;flex:1'>
<input type='text' name='q' value='{htmlmod.escape((self._q(url).get('q') or [''])[0])}' placeholder='Search bookmarks…'></form></div>
{rows}""")

    def apply_bookmarks_act(self, url):
        dq = self._q(url).get("del")
        if dq:
            target = dq[0]
            self.bookmarks = [b for b in self.bookmarks if b.get("url") != target]
            save_json(BOOKMARKS_FILE, self.bookmarks)
            self.refresh_bookmark_bar()
            self.refresh_chrome()
            return True
        return False

    def do_import(self):
        if CImport is None:
            self.status.set_label("◈ Importer unavailable")
            return
        bm, hi = CImport.import_all()
        if not bm and not hi:
            self.status.set_label("◈ No Chrome/Firefox data found to import")
            return
        have_bm = {b.get("url") for b in self.bookmarks}
        added_bm = 0
        for b in bm:
            if b.get("url") and b["url"] not in have_bm:
                have_bm.add(b["url"])
                self.bookmarks.append(b)
                added_bm += 1
        have_hi = {h.get("url") for h in self.history}
        added_hi = 0
        for h in hi:
            if h.get("url") and h["url"] not in have_hi:
                have_hi.add(h["url"])
                self.history.append(h)
                added_hi += 1
        del self.history[:-HISTORY_MAX]
        save_json(BOOKMARKS_FILE, self.bookmarks)
        save_json(HISTORY_FILE, self.history)
        self.refresh_bookmark_bar()
        self.refresh_chrome()
        self.status.set_label(f"◈ Imported {added_bm} bookmarks, {added_hi} history entries")

    def clear_data(self):
        self.history = []
        save_json(HISTORY_FILE, self.history)
        import shutil
        for d in (os.path.expanduser("~/.cache/vixzen-web"),):
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        self._init_blocklist()

    def inspect_page(self):
        v = self.current_view()
        if v is None:
            return
        try:
            v.get_inspector().show()
            self.status.set_label("◈ Developer inspector opened")
        except Exception as e:
            self.status.set_label(f"◈ Inspector unavailable: {e}")

    def render_vixzen_search(self, view, url):
        q = VSearch.query_from_url(url)
        view.load_alternate_html(
            VSearch.results_page_html(q, [], False, VERSION).replace(
                "<div class='n'>0 results</div>", "<div class='n'>searching…</div>"),
            url, None)
        self.url.set_text(q)
        self.status.set_label(f"◈ Vixzen Search: {q}")
        import threading
        def work():
            try:
                results, offline = VSearch.search(q, self.bookmarks, self.history)
            except Exception:
                results, offline = [], True
            GLib.idle_add(lambda: self._show_vixzen_results(view, url, q, results, offline))
        threading.Thread(target=work, daemon=True).start()

    def _history_dirty(self):
        if self._history_timer:
            return
        self._history_timer = GLib.timeout_add_seconds(2, self._flush_history)

    def _flush_history(self):
        self._history_timer = None
        try:
            save_json(HISTORY_FILE, self.history)
        except Exception:
            pass
        return False

    def _show_vixzen_results(self, view, url, q, results, offline):
        try:
            if view.get_uri() not in (url, None) and not (view.get_uri() or "").startswith("vixzen:search"):
                return False  # user moved on; don't clobber
            view.load_alternate_html(VSearch.results_page_html(q, results, offline, VERSION), url, None)
            if results and not offline:
                title = f"Vixzen Search: {q}"
                if not self.history or self.history[-1].get("url") != url:
                    self.history.append({"title": title, "url": url})
                    del self.history[:-HISTORY_MAX]
                    self._history_dirty()
        except Exception:
            pass
        return False

    def load_in_current(self, url):
        view = self.current_view()
        if view is None:
            self.new_tab(url)
        else:
            self.load_in_view(view, url)

    def on_url_enter(self, _entry):
        url = to_url(self.url.get_text())
        if url:
            self.load_in_current(url)

    # ---- webkit signals ----
    def on_load_changed(self, view, event):
        if int(event) == 3:
            self.progress.set_fraction(0.0)
            uri = view.get_uri() or ""
            title = view.get_title() or uri
            if uri and not uri.startswith(("vixzen:", "about:")):
                if not self.history or self.history[-1].get("url") != uri:
                    self.history.append({"title": title, "url": uri})
                    del self.history[:-HISTORY_MAX]
                    self._history_dirty()
        self.refresh_chrome()

    def on_progress(self, view, _pspec):
        try:
            self.progress.set_fraction(float(view.get_estimated_load_progress()))
        except Exception:
            pass

    def on_title(self, view, _pspec):
        try:
            page = getattr(view, "_tab_page", None)
            title = view.get_title() or view.get_uri() or "New Tab"
            if page is not None:
                page.set_title(title[:40])
        except Exception:
            pass
        self.refresh_chrome()

    def on_decide_policy(self, view, decision, dtype):
        try:
            nav = decision.get_navigation_action() if hasattr(decision, "get_navigation_action") else None
            req_uri = ""
            if nav is not None:
                try:
                    req_uri = nav.get_request().get_uri() or ""
                except Exception:
                    req_uri = ""
            if req_uri.startswith("vixzen:") and req_uri != HOME_URL:
                decision.ignore()
                self.render_local(view, req_uri)
                return True
            if hasattr(WK, "PolicyDecisionType") and int(dtype) == int(WK.PolicyDecisionType.NEW_WINDOW_ACTION):
                nav = decision.get_navigation_action() if hasattr(decision, "get_navigation_action") else None
                uri = nav.get_request().get_uri() if nav else None
                if uri:
                    decision.ignore()
                    self.new_tab(uri)
                    return True
        except Exception:
            pass
        return False

    def on_load_failed(self, view, _event, uri, error, *args):
        html = (f"<body style='font-family:sans-serif;background:#12141C;color:#E8EAF2;"
                f"text-align:center;padding:60px'><h2>Couldn't load {uri}</h2>"
                f"<p style='opacity:.7'>{error}</p>"
                f"<p><a style='color:#7C7CFF' href='{HOME_URL}'>← Back to speed dial</a></p></body>")
        view.load_alternate_html(html, uri, None)
        return True

    # ---- chrome ----
    def refresh_chrome(self):
        view = self.current_view()
        if view is None:
            return
        try:
            self.back_btn.set_sensitive(view.can_go_back())
            self.fwd_btn.set_sensitive(view.can_go_forward())
        except Exception:
            pass
        uri = view.get_uri() or ""
        if uri != self._chrome_us.get("uri"):
            self._chrome_us["uri"] = uri
            if uri not in ("", HOME_URL, "vixzen:home", "about:blank"):
                if self.url.get_text() != uri and not self.url.has_focus():
                    self.url.set_text(uri)
        secure = uri.startswith("https://")
        try:
            self.url.set_icon_from_icon_name(
                Gtk.EntryIconPosition.PRIMARY,
                "channel-secure-symbolic" if secure else "channel-insecure-symbolic")
            self.url.set_icon_tooltip_text(
                Gtk.EntryIconPosition.PRIMARY,
                "Secure HTTPS connection" if secure else "Not HTTPS")
        except Exception:
            pass
        title = view.get_title() or uri or "Vixzen Web"
        if title != self._chrome_us.get("title"):
            self._chrome_us["title"] = title
            self.set_title(f"{title} — Vixzen Web")
        page = getattr(view, "_tab_page", None)
        if page is not None and view.get_title():
            page.set_title(view.get_title()[:40])
        self._shield_state()
        starred = any(b.get("url") == uri for b in self.bookmarks)
        if starred != self._chrome_us.get("starred"):
            self._chrome_us["starred"] = starred
            self.star.set_icon_name("starred-symbolic" if starred else "non-starred-symbolic")
        n = self.tabs.get_n_pages()
        self.status.set_label(f"◈ {n} tab{'s' if n != 1 else ''}  •  {uri or 'speed dial'}")

    def on_bookmark(self, _btn):
        view = self.current_view()
        if not view:
            return
        uri = view.get_uri() or ""
        if not uri or uri == HOME_URL:
            return
        if any(b.get("url") == uri for b in self.bookmarks):
            self.bookmarks = [b for b in self.bookmarks if b.get("url") != uri]
            msg = "Bookmark removed"
        else:
            self.bookmarks.append({"title": view.get_title() or uri, "url": uri})
            msg = "Bookmarked ✓"
        save_json(BOOKMARKS_FILE, self.bookmarks)
        self.refresh_bookmark_bar()
        self.refresh_chrome()
        self.status.set_label(f"◈ {msg}: {uri}")

    # ---- tracker blocking (WebKit UserContentFilter) ----
    FILTER_CACHE = os.path.join(os.path.expanduser("~/.cache/vixzen-web"), "filters.json")

    def _init_blocklist(self):
        if not self.block_enabled:
            for v in self.views():
                try:
                    v.get_user_content_manager().remove_all_filters()
                except Exception:
                    pass
            self._shield_state()
            return False
        if BL is None or not self.blocked_hosts:
            self._shield_state()
            return False
        try:
            os.makedirs(os.path.dirname(self.FILTER_CACHE), exist_ok=True)
            with open(self.FILTER_CACHE, "w") as f:
                f.write(BL.compile_apple_json(self.blocked_hosts,
                                              allow_unless=self.allowed_sites))
            store = WK.UserContentFilterStore.new(os.path.dirname(self.FILTER_CACHE))
            store.save_from_file("vixzen", Gio.File.new_for_path(self.FILTER_CACHE),
                                 None, self._on_filter_saved, store)
        except Exception:
            pass
        self._shield_state()
        return False

    def _on_filter_saved(self, store, res, *_a):
        try:
            store.save_finish(res)
            store.load("vixzen", None, self._on_filter_loaded, store)
        except Exception:
            pass

    def _on_filter_loaded(self, store, res, *_a):
        try:
            ucf = store.load_finish(res)
        except Exception:
            return
        self._ucf = ucf
        for v in self.views():
            try:
                ucm = v.get_user_content_manager()
                ucm.remove_all_filters()
                if self.block_enabled:
                    ucm.add_filter(ucf)
            except Exception:
                pass
        self._shield_state()

    def page_host(self):
        v = self.current_view()
        try:
            return (urllib.parse.urlparse(v.get_uri() or "").hostname or "").lower().strip(".") if v else ""
        except Exception:
            return ""

    def toggle_site_block(self):
        page = self.page_host()
        if not page:
            self.status.set_label("◈ Open a site first, then allow/block it")
            return
        if page in self.allowed_sites:
            self.allowed_sites.discard(page)
            msg = f"◈ Blocking trackers on {page} again"
        else:
            self.allowed_sites.add(page)
            msg = f"◈ Trackers allowed on {page} (reload to apply)"
        self.settings["allowed_sites"] = sorted(self.allowed_sites)
        save_settings(self.settings)
        self._init_blocklist()
        v = self.current_view()
        if v is not None:
            try:
                v.reload()
            except Exception:
                pass
        self.status.set_label(msg)

    def _shield_state(self):
        try:
            page = self.page_host()
            state = ("off here" if page in self.allowed_sites
                     else ("on" if self.block_enabled and self._ucf else "starting…"))
            self.shield.set_tooltip_text(f"Tracker blocking: {state} (click: allow/block this site)")
        except Exception:
            pass

    # ---- bookmark bar (Chrome-style) ----
    def refresh_bookmark_bar(self):
        child = self.bm_bar.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.bm_bar.remove(child)
            child = nxt
        if not self.bookmarks:
            lbl = Gtk.Label(label="Bookmark bar — press Ctrl+D on any page to add", xalign=0)
            lbl.set_opacity(0.6)
            self.bm_bar.append(lbl)
            return
        for b in self.bookmarks[:40]:
            title, url = (b.get("title", "") or b.get("url", ""))[:24], b.get("url", "")
            btn = Gtk.Button(label=title or url[:24], tooltip_text=url)
            btn.connect("clicked", lambda _btn, u=url: self.load_in_current(u))
            self.bm_bar.append(btn)

    def _apply_bar_visibility(self):
        self.bm_scroll.set_visible(bool(self.settings.get("bookmark_bar", True)))

    def toggle_bar(self):
        self.settings["bookmark_bar"] = not self.settings.get("bookmark_bar", True)
        save_settings(self.settings)
        self._apply_bar_visibility()

    # ---- omnibox suggestions ----
    def _on_url_typed(self, entry):
        if self._suggest_pending:
            try:
                GLib.source_remove(self._suggest_pending)
            except Exception:
                pass
            self._suggest_pending = None
        self._suggest_pending = GLib.timeout_add(280, self._fetch_suggest)

    def _fetch_suggest(self):
        self._suggest_pending = None
        text = self.url.get_text().strip()
        if text == self._chrome_us.get("sug_q"):
            return False
        self._chrome_us["sug_q"] = text
        if len(text) < 2 or "://" in text or text == HOME_URL:
            self.suggest_pop.popdown()
            return False
        self._suggest_token += 1
        token = self._suggest_token
        engine = self.settings.get("engine", "vixzen")
        if engine == "vixzen" and VSearch is not None:
            sug = VSearch.local_suggest(text, self.bookmarks, self.history)
            self._show_suggest(token, text, sug)
            return False
        import threading
        def work():
            sug = fetch_suggestions(text, engine)
            GLib.idle_add(lambda: self._show_suggest(token, text, sug))
        threading.Thread(target=work, daemon=True).start()
        return False

    def _show_suggest(self, token, text, sug):
        if token != self._suggest_token:
            return False
        child = self.suggest_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.suggest_box.remove(child)
            child = nxt
        if not sug:
            self.suggest_pop.popdown()
            return False
        for s in sug:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=s[:70], xalign=0,
                                    ellipsize=Pango.EllipsizeMode.END))
            row._query = s
            self.suggest_box.append(row)
        self.suggest_pop.popup()
        return False

    def _on_suggest_pick(self, _box, row):
        q = getattr(row, "_query", "")
        if q:
            self.suggest_pop.popdown()
            self.load_in_current(search_url(q, self.settings.get("engine", "vixzen")))

    def show_search_engine(self):
        dlg = Adw.MessageDialog.new(self, "Search engine")
        box = Gtk.ListBox()
        box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        rows = {}
        for key, spec in SEARCH_ENGINES.items():
            row = Gtk.ListBoxRow()
            mark = "● " if key == self.settings.get("engine") else "○ "
            row.set_child(Gtk.Label(label=f"{mark}{spec['name']}", xalign=0))
            row._engine = key
            box.append(row)
            rows[key] = row
        scroll = Gtk.ScrolledWindow(child=box)
        scroll.set_size_request(300, 200)
        dlg.set_extra_child(scroll)
        dlg.add_response("close", "Close")
        def picked(_b, r):
            if r and getattr(r, "_engine", None):
                self.settings["engine"] = r._engine
                save_settings(self.settings)
                self.refresh_chrome()
        box.connect("row-activated", picked)
        dlg.present()

    # ---- tabs: close tracking, duplicate, pin, menu ----
    def on_tab_closing(self, _tabview, page):
        try:
            v = self._view_for_page(page)
            uri = v.get_uri() if v else ""
            if uri and uri.startswith("http"):
                self.closed_stack.append({"title": v.get_title() or uri, "url": uri})
                del self.closed_stack[:-CLOSED_MAX]
        except Exception:
            pass
        return False

    def reopen_closed(self):
        if not self.closed_stack:
            self.status.set_label("◈ Nothing to reopen")
            return
        item = self.closed_stack.pop()
        self.new_tab(item.get("url", HOME_URL))

    def duplicate_tab(self):
        v = self.current_view()
        if v:
            self.new_tab(v.get_uri() or HOME_URL)

    def toggle_pin(self):
        page = self.tabs.get_selected_page()
        if page is None:
            return
        try:
            self.tabs.set_page_pinned(page, not page.get_pinned())
        except Exception:
            pass

    def close_others(self):
        page = self.tabs.get_selected_page()
        if page is not None:
            try:
                self.tabs.close_other_pages(page)
            except Exception:
                pass

    def on_tabbar_right_click(self, _g, _n, x, y):
        pop = Gtk.PopoverMenu.new_from_model(self._tab_menu_model())
        pop.set_parent(self.tabbar)
        pop.set_pointing_to(Gdk.Rectangle(int(x), int(y), 1, 1))
        pop.popup()

    def _tab_menu_model(self):
        m = Gio.Menu()
        m.append("Duplicate tab", "win.duplicate-tab")
        m.append("Pin / unpin tab", "win.pin-tab")
        m.append("Reopen closed tab (Ctrl+Shift+T)", "win.reopen-closed")
        m.append("Close other tabs", "win.close-others")
        m.append("New tab (Ctrl+T)", "win.new-tab")
        return m

    def _on_close_save_session(self, *_a):
        try:
            urls = []
            for v in self.views():
                u = v.get_uri() or ""
                if u.startswith("http") and u not in urls:
                    urls.append(u)
            with open(SESSION_FILE, "w") as f:
                json.dump(urls[:25], f)
        except Exception:
            pass
        return False

    def open_session(self, urls):
        for u in (urls or [])[:12]:
            if isinstance(u, str) and u.startswith("http"):
                self.new_tab(u)

    # ---- find / zoom ----
    def find_controller(self):
        view = self.current_view()
        if view is None:
            return None
        try:
            return view.get_find_controller()
        except Exception:
            return None

    def on_find_changed(self, entry):
        ctl = self.find_controller()
        if ctl is None:
            return
        text = entry.get_text()
        if not text:
            try:
                ctl.search_finish()
            except Exception:
                pass
            return
        try:
            opts = WK.FindOptions.WRAP_AROUND | WK.FindOptions.HIGHLIGHT_DIALOG
            ctl.search(text, opts, 100)
        except Exception:
            pass

    def find_next(self):
        ctl = self.find_controller()
        if ctl:
            try:
                ctl.search_next()
            except Exception:
                pass

    def find_prev(self):
        ctl = self.find_controller()
        if ctl:
            try:
                ctl.search_previous()
            except Exception:
                pass

    def zoom(self, delta):
        view = self.current_view()
        if view:
            try:
                view.set_zoom_level(max(0.3, min(3.0, view.get_zoom_level() + delta)))
            except Exception:
                pass

    def zoom_reset(self):
        view = self.current_view()
        if view:
            try:
                view.set_zoom_level(1.0)
            except Exception:
                pass

    # ---- dialogs ----
    def _list_dialog(self, title, items, on_pick):
        dlg = Adw.MessageDialog.new(self, title)
        box = Gtk.ListBox()
        box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        for it in items[-50:][::-1]:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=f"{it.get('title', '')[:40]} — {it.get('url', '')[:60]}",
                            xalign=0, ellipsize=Pango.EllipsizeMode.END)
            row.set_child(lbl)
            row._url = it.get("url", "")
            box.append(row)
        box.set_size_request(420, 280)
        scroll = Gtk.ScrolledWindow(child=box)
        scroll.set_size_request(420, 280)
        dlg.set_extra_child(scroll)
        dlg.add_response("close", "Close")
        def picked(_b, r):
            if r and r._url:
                on_pick(r._url)
        box.connect("row-activated", picked)
        dlg.present()

    def show_bookmarks(self):
        self._list_dialog("Bookmarks", self.bookmarks, self.load_in_current)

    def show_history(self):
        self._list_dialog("History", self.history, self.load_in_current)

    def show_tabs_overview(self):
        items = []
        for i in range(self.tabs.get_n_pages()):
            page = self.tabs.get_nth_page(i)
            v = self._view_for_page(page)
            t = (v.get_title() if v else None) or (v.get_uri() if v else "") or f"Tab {i+1}"
            u = v.get_uri() if v else ""
            items.append({"title": f"{i+1}. {t}", "url": u, "_page": page})
        dlg = Adw.MessageDialog.new(self, f"Tabs ({len(items)})")
        box = Gtk.ListBox()
        for it in items:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=f"{it['title'][:60]}", xalign=0,
                                    ellipsize=Pango.EllipsizeMode.END))
            row._page = it["_page"]
            box.append(row)
        scroll = Gtk.ScrolledWindow(child=box)
        scroll.set_size_request(440, 280)
        dlg.set_extra_child(scroll)
        dlg.add_response("close", "Close")
        box.connect("row-activated", lambda _b, r: self.tabs.set_selected_page(r._page))
        dlg.present()

    def show_welcome(self):
        self.settings["welcomed"] = True
        save_settings(self.settings)
        d = Adw.MessageDialog.new(self, "Welcome to Vixzen Web")
        d.set_body("Just three things:\n\n"
                   "• Type in the top bar to search or go anywhere.\n"
                   "• Star (☆) saves a page to your bookmark bar.\n"
                   "• Ctrl+T opens a tab, Ctrl+Shift+T brings one back.\n\n"
                   "Everything is private — Vixzen Search keeps no log.")
        d.add_response("ok", "Start browsing")
        d.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        d.present()
        return False

    def show_about(self):
        d = Adw.AboutWindow(transient_for=self, application_name="Vixzen Web",
                            version=VERSION, developer_name="VixzenOS",
                            comments="Simple, private web browser. Google-style layout, Vixzen Search built in.",
                            website="https://vixzen-os.example/")
        d.present()

    def add_shortcuts(self):
        ctl = Gtk.ShortcutController.new()
        ctl.set_scope(Gtk.ShortcutScope.LOCAL)
        self.add_controller(ctl)
        def sc(trigger, fn):
            ctl.add_shortcut(Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string(trigger),
                Gtk.CallbackAction.new(lambda *_: (fn(), True)[1])))
        sc("<Control>l", lambda: self.url.grab_focus())
        sc("<Control>t", lambda: self.new_tab(HOME_URL))
        sc("<Control>w", self.close_tab)
        sc("<Control><Shift>t", self.reopen_closed)
        sc("<Control><Shift>b", self.toggle_bar)
        sc("<Control>Tab", self.next_tab)
        sc("<Control><Shift>Tab", self.prev_tab)
        sc("<Control>1", lambda: self.goto_tab(0))
        sc("<Control>2", lambda: self.goto_tab(1))
        sc("<Control>3", lambda: self.goto_tab(2))
        sc("<Control>4", lambda: self.goto_tab(3))
        sc("<Control>5", lambda: self.goto_tab(4))
        sc("<Control>6", lambda: self.goto_tab(5))
        sc("<Control>7", lambda: self.goto_tab(6))
        sc("<Control>8", lambda: self.goto_tab(7))
        sc("<Control>9", lambda: self.goto_tab(-1))
        sc("<Control>r", lambda: self.current_view() and self.current_view().reload())
        sc("<Control>f", lambda: (self.findbar.show(), self.find_entry.grab_focus()))
        sc("Escape", lambda: self.findbar.hide())
        sc("<Control>d", lambda: self.on_bookmark(None))
        sc("<Control>comma", lambda: self.load_in_current("vixzen:settings"))
        sc("<Control>h", lambda: self.load_in_current("vixzen:history"))
        sc("<Control><Shift>o", lambda: self.load_in_current("vixzen:bookmarks"))
        sc("<Control><Shift>Delete", lambda: (self.clear_data(), self.load_in_current("vixzen:settings")))
        sc("<Control><Shift>i", self.inspect_page)
        sc("<Control><Shift>a", self.show_tabs_overview)
        sc("<Alt>Left", lambda: self.current_view() and self.current_view().go_back())
        sc("<Alt>Right", lambda: self.current_view() and self.current_view().go_forward())
        sc("<Alt>Home", lambda: self.load_in_current(HOME_URL))
        sc("<Control>plus", lambda: self.zoom(0.1))
        sc("<Control>minus", lambda: self.zoom(-0.1))
        sc("<Control>0", self.zoom_reset)

    def next_tab(self):
        n = self.tabs.get_n_pages()
        if n > 1:
            i = self._selected_index()
            self.tabs.set_selected_page(self.tabs.get_nth_page((i + 1) % n))

    def prev_tab(self):
        n = self.tabs.get_n_pages()
        if n > 1:
            i = self._selected_index()
            self.tabs.set_selected_page(self.tabs.get_nth_page((i - 1) % n))

    def goto_tab(self, i):
        n = self.tabs.get_n_pages()
        if n == 0:
            return
        page = self.tabs.get_nth_page(n - 1 if i == -1 else min(i, n - 1))
        if page is not None:
            self.tabs.set_selected_page(page)

    def _selected_index(self):
        sel = self.tabs.get_selected_page()
        for i in range(self.tabs.get_n_pages()):
            if self.tabs.get_nth_page(i) == sel:
                return i
        return 0

    def close_tab(self):
        page = self.tabs.get_selected_page()
        if page is None:
            return
        try:
            v = self._view_for_page(page)
            uri = v.get_uri() if v else ""
            if uri and uri.startswith("http"):
                self.closed_stack.append({"title": v.get_title() or uri, "url": uri})
                del self.closed_stack[:-CLOSED_MAX]
        except Exception:
            pass
        if self.tabs.get_n_pages() <= 1:
            self.close()
        else:
            self.tabs.close_page(page)


def load_session():
    try:
        with open(SESSION_FILE) as f:
            urls = json.load(f)
            return [u for u in urls if isinstance(u, str) and u.startswith("http")][:25]
    except Exception:
        return []


class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.start = HOME_URL
        self.rest = []
        given = False
        for a in sys.argv[1:]:
            if a == "--smoke":
                continue
            if not a.startswith("-"):
                u = to_url(a)
                if u:
                    self.start = u
                    given = True
                break
        if not given and load_settings().get("startup", "newtab") == "restore":
            sess = load_session()
            if sess:
                self.start, self.rest = sess[0], sess[1:12]

    def do_activate(self):
        win = BrowserWin(self, self.start)
        win.present()
        if self.rest:
            GLib.idle_add(lambda: (win.open_session(self.rest), False)[1])


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        ensure_config()
        assert callable(to_url)
        assert to_url("example.com") == "https://example.com"
        assert "hello" in to_url("hello world")  # engine-aware, respects saved setting
        assert to_url("vixzen:search?q=x") == "vixzen:search?q=x"
        assert search_url("hello", "vixzen").startswith("vixzen:search?q=")
        assert to_url(HOME_URL) == HOME_URL
        assert "Vixzen" in start_page_html()
        assert "dial" in start_page_html([{"title": "T", "url": "https://example.com"}], []).lower()
        assert search_url("hello", "google").startswith("https://www.google.com/")
        assert search_url("hello", "bing").startswith("https://www.bing.com/")
        assert load_settings()["engine"] in SEARCH_ENGINES
        assert to_url("vixzen:settings") == "vixzen:settings"
        assert to_url("vixzen:history?q=x") == "vixzen:history?q=x"
        # session roundtrip (restore path)
        with open(SESSION_FILE, "w") as f:
            json.dump(["https://example.com/", "not-a-url", 42], f)
        assert load_session() == ["https://example.com/"]
        os.unlink(SESSION_FILE)
        assert load_session() == []
        # chrome:// pages render without a window (pure HTML builders need
        # self — exercise via lightweight namespace instead)
        print(f"web smoke OK v{VERSION} (WebKit API v{WK_API})")
    else:
        App().run([sys.argv[0]])
