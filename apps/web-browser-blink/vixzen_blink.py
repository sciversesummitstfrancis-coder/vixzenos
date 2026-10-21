#!/usr/bin/env python3
"""Vixzen Blink v0.5 (EXPERIMENTAL) — real Chromium/Blink engine for VixzenOS.
Run: python3 apps/web-browser-blink/vixzen_blink.py [url] [--smoke]

Why a second app: Blink only ships inside Chromium. QtWebEngine wraps real
Chromium/Blink (proven here: Chrome/140). This mirrors Vixzen Web's features
(tabs, omnibox + suggestions, bookmark bar, history, Vixzen Search, downloads,
find, zoom, Chrome shortcuts) on the Blink engine for Chrome-only sites
(Meet, banking, DRM video).

Strategy: Vixzen Web (WebKit, ~168MB, GTK Liquid Glass) stays the default.
Blink (~2-3x RAM, Qt Fusion styling) is the fallback. Shared data: the same
~/.config/vixzen-web/{bookmarks,history,settings}.json, so both apps stay in
sync and Vixzen Search works identically (vixzen_search.py is engine-agnostic).

Needs: PyQt6 + PyQt6-WebEngine (pip) or python3-pyside6 + qt6-qtwebengine.
"""
import os
import sys
import json
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "web-browser"))
sys.path.insert(0, os.path.expanduser("~/.local/share/vixzen-blink"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # installed sibling copy

# ---- shared logic: gi-free web_core (Qt+GTK must never mix in one process) ----
from web_core import (to_url, search_url, load_settings, save_settings,
    load_json, ensure_config, start_page_html, SEARCH_ENGINES, SETTINGS_FILE,
    BOOKMARKS_FILE, HISTORY_FILE, HISTORY_MAX, HOME_URL, CLOSED_MAX,
    fetch_suggestions as _w_fetch_suggestions)
try:
    import vixzen_search as VSearch
except Exception:
    VSearch = None
try:
    import blocklist as BL
except Exception:
    BL = None

APP_ID = "os.vixzen.blink"
VERSION = "0.5"
APP_NAME = "Vixzen Blink"


def _load(name, default):
    try:
        with open(name) as f:
            d = json.load(f)
            return d if isinstance(d, type(default)) else default
    except Exception:
        return default


def _save(name, data):
    try:
        os.makedirs(os.path.dirname(name), exist_ok=True)
        with open(name, "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass


# ---- Qt binding shim (PyQt6 primary, PySide6 fallback) ----
QT_BINDING = None
try:
    from PyQt6.QtWidgets import *  # noqa
    from PyQt6.QtCore import Qt, QUrl, QTimer, QStringListModel, QThread
    from PyQt6.QtGui import QAction, QKeySequence, QDesktopServices, QShortcut, QCursor
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import (
        QWebEnginePage, QWebEngineProfile, QWebEngineDownloadRequest,
        QWebEngineUrlRequestInterceptor)
    QT_BINDING = "PyQt6"
except ImportError:
    from PySide6.QtWidgets import *  # noqa
    from PySide6.QtCore import Qt, QUrl, QTimer, QStringListModel, QThread
    from PySide6.QtGui import QAction, QKeySequence, QDesktopServices, QShortcut, QCursor
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import (
        QWebEnginePage, QWebEngineProfile, QWebEngineDownloadRequest,
        QWebEngineUrlRequestInterceptor)
    QT_BINDING = "PySide6"

if QT_BINDING == "PyQt6":
    from PyQt6.QtCore import pyqtSignal as Signal
else:
    from PySide6.QtCore import Signal


CHROME_QSS = """
QMainWindow, QWidget#central { background: #D4D9E3; color: #202124; }
QTabWidget::pane { border: none; background: #FFFFFF; }
QTabBar::tab { background: transparent; border: none;
    border-top-left-radius: 10px; border-top-right-radius: 10px; padding: 6px 16px; color: #5F6368; }
QTabBar::tab:selected { background: #FFFFFF; color: #202124; }
QTabBar::tab:hover:!selected { background: rgba(32,33,36,0.08); }
QLineEdit#omnibox { border-radius: 16px; padding: 7px 16px; font-size: 14px;
    background: #F1F3F4; border: 1px solid transparent; color: #202124; }
QLineEdit#omnibox:focus { border: 1px solid #1A73E8; background: #FFFFFF; }
QToolButton, QPushButton { border-radius: 12px; padding: 6px; color: #5F6368;
    background: transparent; border: none; }
QToolButton:hover, QPushButton:hover { background: rgba(32,33,36,0.08); }
QToolBar { spacing: 2px; background: #FFFFFF; border: none; }
QLabel#status { color: #5F6368; padding: 2px 10px; }
QToolButton#avatar { background: #8E24AA; color: #FFFFFF; border-radius: 14px;
    font-weight: 800; font-size: 14px; }
QToolButton#avatar:hover { background: #9C27B0; }
QScrollArea#bmbar { background: #FFFFFF; border: none; border-bottom: 1px solid #DADCE0; }
QProgressBar { border: 0; background: transparent; height: 3px; text-align: center; }
QProgressBar::chunk { background: #1A73E8; }
QMenu { background: #FFFFFF; color: #202124; }
QListView, QLineEdit { background: #FFFFFF; color: #202124; }
"""
DARK_QSS = """
QMainWindow, QWidget#central { background: #12141C; color: #E8EAF2; }
QTabWidget::pane { border: 1px solid rgba(255,255,255,36); border-radius: 14px;
    background: #161927; }
QTabBar::tab { background: rgba(255,255,255,14); border: 1px solid rgba(255,255,255,28);
    border-top-left-radius: 10px; border-top-right-radius: 10px; padding: 6px 14px; }
QTabBar::tab:selected { background: rgba(124,124,255,70); }
QLineEdit#omnibox { border-radius: 16px; padding: 7px 16px; font-size: 14px;
    background: rgba(10,12,20,150); border: 1px solid rgba(255,255,255,45); color: #E8EAF2; }
QLineEdit#omnibox:focus { border: 1px solid #7C7CFF; }
QToolButton, QPushButton { border-radius: 12px; padding: 6px; }
QToolBar { spacing: 4px; }
QLabel#status { color: rgba(232,234,242,160); padding: 2px 10px; }
QFrame#rail { background: #14161F; border-radius: 16px; }
QFrame#rail QToolButton { border-radius: 999px; font-size: 16px; padding: 8px;
  color: #C9CEE0; background: transparent; border: 1px solid transparent; }
QFrame#rail QToolButton:hover { background: rgba(124,124,255,90); }
QFrame#rail QToolButton:checked { background: rgba(124,124,255,120);
  border: 1px solid rgba(255,255,255,60); color: #FFFFFF; }
QProgressBar { border: 0; background: transparent; height: 3px; text-align: center; }
QProgressBar::chunk { background: #7C7CFF; }
"""


class BlinkPage(QWebEnginePage):
    """Intercepts vixzen: URLs (home/search) and renders them locally."""

    def __init__(self, win, profile):
        super().__init__(profile, win)
        self.win = win

    def acceptNavigationRequest(self, url, _type, _main):
        s = url.toString()
        if s == HOME_URL or s == "vixzen://home":
            self.win.render_home(self.win.view_of(self))
            return False
        if s.startswith("vixzen:search"):
            self.win.render_search(self.win.view_of(self), s)
            return False
        return True


class BlockInterceptor(QWebEngineUrlRequestInterceptor):
    """Host-list tracker blocking with per-site allowlist + counting."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win

    def interceptRequest(self, info):
        try:
            w = self.win
            if BL is None or not w.block_enabled or not w.blocked_hosts:
                return
            host = (info.requestUrl().host() or "").lower().strip(".")
            if not host or not BL.matches(host, w.blocked_hosts):
                return
            try:
                fp = (info.firstPartyUrl().host() or "").lower().strip(".")
            except Exception:
                fp = ""
            if fp and (fp == host or fp.endswith("." + host) or host.endswith("." + fp)):
                return  # first-party: same site, never block
            if w.page_host() in w.allowed_sites:
                return
            info.block(True)
            w.note_blocked(host)
        except RuntimeError:
            pass


class BrowserWin(QMainWindow):
    def __init__(self, start_url):
        super().__init__()
        ensure_config()
        self.bookmarks = load_json(BOOKMARKS_FILE, [])
        self.history = load_json(HISTORY_FILE, [])
        self.settings = load_settings()
        self.closed_stack = []
        self.download_items = []
        self.settings.setdefault("allowed_sites", [])
        self.allowed_sites = set(self.settings.get("allowed_sites", []))
        self.block_enabled = True
        self.blocked_hosts = BL.get_hosts() if BL is not None else set()
        self.blocked_total = 0
        self._shield_timer = None
        self._hist_timer = None
        self._sug_last = None
        self.setWindowTitle("Vixzen Blink")
        self.resize(1150, 730)
        self.apply_theme()

        self.profile = QWebEngineProfile.defaultProfile()
        try:
            self.profile.downloadRequested.connect(self.on_download)
        except Exception:
            pass
        try:
            self._interceptor = BlockInterceptor(self)
            self.profile.setUrlRequestInterceptor(self._interceptor)
        except Exception:
            pass

        central = QWidget(objectName="central")
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._ws_btns = []

        # tab strip (tabs live here; page content lives in self.stack below
        # the toolbar — Chrome order: tabs, toolbar, bookmarks, page, status)
        tabrow = QHBoxLayout()
        self.tabbar = QTabBar()
        self.tabbar.setTabsClosable(True)
        self.tabbar.setMovable(True)
        self.tabbar.setExpanding(False)
        self.tabbar.tabCloseRequested.connect(self.close_tab_index)
        self.tabbar.currentChanged.connect(self._on_tab_selected)
        self.tabbar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabbar.customContextMenuRequested.connect(self.tab_menu)
        tabrow.addWidget(self.tabbar, 1)
        self.stack = QStackedWidget()
        newtab = QToolButton(text="+", toolTip="New tab (Ctrl+T)")
        newtab.clicked.connect(lambda _c=False: self.new_tab(HOME_URL))
        tabrow.addWidget(newtab)
        lay.addLayout(tabrow)

        # toolbar
        bar = QToolBar()
        bar.setMovable(False)
        self.act_back = bar.addAction("‹", self.go_back)
        self.act_back.setToolTip("Back (Alt+Left)")
        self.act_fwd = bar.addAction("›", self.go_fwd)
        self.act_fwd.setToolTip("Forward (Alt+Right)")
        self.act_reload = bar.addAction("⟳", self.go_reload)
        self.act_reload.setToolTip("Reload (Ctrl+R)")
        self.act_home = bar.addAction("⌂", lambda _a=False: self.load_in_current(HOME_URL))
        self.act_home.setToolTip("Home (Alt+Home)")
        self.url = QLineEdit(objectName="omnibox",
                             placeholderText="Search Vixzen or type a web address  (Ctrl+L)")
        self.url.returnPressed.connect(self.on_url_enter)
        self.url.textEdited.connect(self.on_url_typed)
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.completer.activated.connect(self.on_suggest_pick)
        self.url.setCompleter(self.completer)
        try:
            from PyQt6.QtGui import QIcon as _QIcon
        except Exception:
            from PySide6.QtGui import QIcon as _QIcon
        self.lock_act = QAction("lock", self)
        self.lock_act.setToolTip("Connection security")
        self.url.addAction(self.lock_act, QLineEdit.ActionPosition.LeadingPosition)
        bar.addWidget(self.url)
        self.shield = QToolButton(text="🛡", toolTip="Trackers blocked this session (click: allow/block this site)")
        self.shield.clicked.connect(lambda _c=False: self.toggle_site_block())
        bar.addWidget(self.shield)
        self.act_star = bar.addAction("☆", self.on_bookmark)
        self.act_star.setToolTip("Bookmark this page (Ctrl+D)")
        bar.addAction("⋮", self.app_menu).setToolTip("Menu")
        self.avatar = QToolButton(objectName="avatar", text="V")
        self.avatar.setToolTip("Profile — local only")
        self.avatar.clicked.connect(lambda _c=False: self.show_about())
        bar.addWidget(self.avatar)
        lay.addWidget(bar)

        # bookmark bar
        self.bm_scroll = QScrollArea(objectName="bmbar")
        self.bm_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.bm_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.bm_scroll.setFixedHeight(34)
        self.bm_scroll.setWidgetResizable(True)
        self.bm_bar = QWidget()
        self.bm_layout = QHBoxLayout(self.bm_bar)
        self.bm_layout.setContentsMargins(4, 0, 4, 0)
        self.bm_scroll.setWidget(self.bm_bar)
        lay.addWidget(self.bm_scroll)
        lay.addWidget(self.stack, 1)
        self.refresh_bookmark_bar()

        # progress + status
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        lay.addWidget(self.progress)
        self.status = QLabel("◈ Vixzen Blink (experimental Blink engine)", objectName="status")
        lay.addWidget(self.status)

        # find bar
        self.findbar = QWidget()
        fl = QHBoxLayout(self.findbar)
        fl.setContentsMargins(0, 0, 0, 0)
        self.find_entry = QLineEdit(placeholderText="Find in page…")
        self.find_entry.textChanged.connect(lambda t: self.find_next(t) if t else self.find_clear())
        self.find_entry.returnPressed.connect(lambda _c=False: self.find_next())
        fl.addWidget(self.find_entry, 1)
        for label, fn in (("Next", lambda: self.find_next()),
                          ("Close", self.findbar.hide)):
            b = QPushButton(label)
            b.clicked.connect(lambda _c, f=fn: f())
            fl.addWidget(b)
        self.findbar.hide()
        lay.addWidget(self.findbar)

        self.add_shortcuts()
        self.apply_bar_visibility()
        self.new_tab(start_url or HOME_URL)

    def appearance(self):
        return self.settings.get("appearance", "chrome")

    def toggle_appearance(self):
        self.settings["appearance"] = "glass" if self.appearance() == "chrome" else "chrome"
        save_settings(self.settings)
        self.apply_theme()
        self.status.setText(f"◈ Appearance: {self.appearance()}")

    def apply_theme(self):
        try:
            self.setStyleSheet(CHROME_QSS if self.appearance() == "chrome" else DARK_QSS)
        except Exception:
            pass

    # ---- views ----
    def make_view(self):
        v = QWebEngineView()
        page = BlinkPage(self, self.profile)
        v.setPage(page)
        v.loadProgress.connect(lambda p, vw=v: self.on_progress(vw, p))
        v.urlChanged.connect(lambda _u, vw=v: self.refresh_chrome())
        v.titleChanged.connect(lambda _t, vw=v: self.on_title(vw))
        return v

    def view_of(self, page):
        for i in range(self.stack.count()):
            v = self.stack.widget(i)
            if v and v.page() is page:
                return v
        return self.current_view()

    def current_view(self):
        w = self.stack.currentWidget()
        return w if isinstance(w, QWebEngineView) else None

    def new_tab(self, url):
        v = self.make_view()
        i = self.stack.addWidget(v)
        self.tabbar.addTab("New Tab")
        self._select(i)
        self.load_in_view(v, url)
        return v

    def load_in_view(self, v, url):
        if url == HOME_URL:
            self.render_home(v)
        elif url.startswith("vixzen:search") and VSearch is not None:
            self.render_search(v, url)
        else:
            v.setUrl(QUrl(url))

    def load_in_current(self, url):
        v = self.current_view()
        if v is None:
            self.new_tab(url)
        else:
            self.load_in_view(v, url)

    def render_home(self, v):
        v.setHtml(start_page_html(self.bookmarks, self.history, self.appearance()), QUrl(HOME_URL))
        self.url.setText("")
        self.status.setText("◈ New tab — search above")

    def render_search(self, v, url):
        q = VSearch.query_from_url(url)
        v.setHtml(VSearch.results_page_html(q, [], False, VERSION), QUrl(url))
        self.url.setText(q)
        self.status.setText(f"◈ Vixzen Search: {q}")

        self._run_search_worker(v, url, q)

    def _run_search_worker(self, v, url, q):
        if VSearch is None:
            return
        worker = _SearchThread(self, q, list(self.bookmarks), list(self.history))
        worker.finished_ok.connect(
            lambda packed, _tok, vw=v, u=url, qq=q: self._show_search_results(vw, u, qq, *packed))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _show_search_results(self, v, url, q, results, offline):
        try:
            cur = v.url().toString()
        except RuntimeError:
            return
        if cur not in (url,) and not cur.startswith("vixzen:search"):
            return
        v.setHtml(VSearch.results_page_html(q, results, offline, VERSION), QUrl(url))
        if results and not offline:
            self.record_history(f"Vixzen Search: {q}", url)

    # ---- chrome ----
    def refresh_chrome(self):
        v = self.current_view()
        if v is None:
            return
        try:
            self.act_back.setEnabled(v.history().canGoBack())
            self.act_fwd.setEnabled(v.history().canGoForward())
        except Exception:
            pass
        try:
            uri = v.url().toString()
        except RuntimeError:
            return
        if uri not in ("", HOME_URL, "vixzen:home", "about:blank") and not uri.startswith("vixzen:"):
            if self.url.text() != uri and not self.url.hasFocus():
                self.url.setText(uri)
        secure = uri.startswith("https://")
        try:
            from PyQt6.QtGui import QIcon as _QIcon2
        except Exception:
            from PySide6.QtGui import QIcon as _QIcon2
        self.lock_act.setIcon(_QIcon2.fromTheme(
            "channel-secure-symbolic" if secure else "channel-insecure-symbolic"))
        self.lock_act.setToolTip("Secure HTTPS connection" if secure else "Not HTTPS")
        title = v.title() or uri or "Vixzen Blink"
        self.setWindowTitle(f"{title} — Vixzen Blink")
        i = self.stack.indexOf(v)
        if i >= 0 and v.title():
            self.tabbar.setTabText(i, v.title()[:32])
        starred = any(b.get("url") == uri for b in self.bookmarks)
        self.act_star.setText("★" if starred else "☆")
        n = self.stack.count()
        self.status.setText(f"◈ {n} tab{'s' if n != 1 else ''}  •  {uri or 'new tab'}")

    def on_progress(self, v, p):
        if v is self.current_view():
            self.progress.setValue(p)
            if p >= 100:
                self.progress.setValue(0)
                try:
                    self.record_history(v.title() or v.url().toString(), v.url().toString())
                except RuntimeError:
                    pass
                self.refresh_chrome()

    def on_title(self, v):
        i = self.stack.indexOf(v)
        if i >= 0 and v.title():
            self.tabbar.setTabText(i, v.title()[:32])
        if v is self.current_view():
            self.refresh_chrome()

    def record_history(self, title, uri):
        if not uri or uri.startswith(("vixzen:", "about:", "data:")):
            if uri.startswith("vixzen:search"):
                pass
            else:
                return
        if not self.history or self.history[-1].get("url") != uri:
            self.history.append({"title": title, "url": uri})
            del self.history[:-HISTORY_MAX]
            if self._hist_timer is None:
                self._hist_timer = QTimer.singleShot(2000, self.flush_history)

    def flush_history(self):
        self._hist_timer = None
        _save(HISTORY_FILE, self.history)

    def on_url_enter(self):
        url = to_url(self.url.text())
        if url:
            self.completer.popup().hide() if self.completer.popup().isVisible() else None
            self.load_in_current(url)

    def on_url_typed(self, _text=None):
        text = self.url.text().strip()
        if text == self._sug_last:
            return
        self._sug_last = text
        if len(text) < 2 or "://" in text or text == HOME_URL:
            return
        engine = self.settings.get("engine", "vixzen")
        if engine == "vixzen" and VSearch is not None:
            sug = VSearch.local_suggest(text, self.bookmarks, self.history)
            self.completer.setModel(QStringListModel(sug))
        elif _w_fetch_suggestions is not None:
            self._sug_token = getattr(self, "_sug_token", 0) + 1
            w = _WorkerThread(self, self._sug_token, _w_fetch_suggestions, text, engine)
            w.finished_ok.connect(
                lambda res, tok: self._show_remote_suggest(tok, res or []))
            w.finished.connect(w.deleteLater)
            w.start()

    def _show_remote_suggest(self, token, sug):
        if token != getattr(self, "_sug_token", -1):
            return
        self.completer.setModel(QStringListModel([s for s in sug if isinstance(s, str)][:8]))

    def on_suggest_pick(self, text):
        self.load_in_current(search_url(text, self.settings.get("engine", "vixzen")))

    # ---- tracker blocking ----
    def page_host(self):
        v = self.current_view()
        try:
            return (v.url().host() or "").lower().strip(".") if v else ""
        except RuntimeError:
            return ""

    def note_blocked(self, host):
        self.blocked_total += 1
        if self._shield_timer is None:
            self._shield_timer = QTimer.singleShot(800, self.flush_shield)

    def flush_shield(self):
        self._shield_timer = None
        try:
            page = self.page_host()
            state = "off here" if page in self.allowed_sites else ("off" if not self.block_enabled else "on")
            self.shield.setToolTip(
                f"Blocked {self.blocked_total} tracker requests · blocking {state} (click: allow/block this site)")
            self.shield.setText(f"🛡{self.blocked_total}" if self.blocked_total else "🛡")
        except RuntimeError:
            pass

    def toggle_site_block(self):
        page = self.page_host()
        if not page:
            self.status.setText("◈ Open a site first, then allow/block it")
            return
        if page in self.allowed_sites:
            self.allowed_sites.discard(page)
            msg = f"◈ Blocking trackers on {page} again"
        else:
            self.allowed_sites.add(page)
            msg = f"◈ Trackers allowed on {page} (reload to apply)"
        self.settings["allowed_sites"] = sorted(self.allowed_sites)
        save_settings(self.settings)
        self.flush_shield()
        self.status.setText(msg)
        v = self.current_view()
        if v is not None:
            v.reload()

    # ---- bookmarks ----
    def refresh_bookmark_bar(self):
        while self.bm_layout.count():
            item = self.bm_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.bookmarks:
            self.bm_layout.addWidget(QLabel("Bookmark bar — star (☆) any page to pin it here"))
            return
        for b in self.bookmarks[:40]:
            title, url = (b.get("title", "") or b.get("url", ""))[:24], b.get("url", "")
            btn = QToolButton(text=title or url[:24])
            btn.setToolTip(url)
            btn.clicked.connect(lambda _c, u=url: self.load_in_current(u))
            self.bm_layout.addWidget(btn)
        self.bm_layout.addStretch(1)

    def apply_bar_visibility(self):
        self.bm_scroll.setVisible(bool(self.settings.get("bookmark_bar", True)))

    def toggle_bar(self, _a=False):
        self.settings["bookmark_bar"] = not self.settings.get("bookmark_bar", True)
        save_settings(self.settings)
        self.apply_bar_visibility()

    def on_bookmark(self, _a=False):
        v = self.current_view()
        if v is None:
            return
        try:
            uri = v.url().toString()
        except RuntimeError:
            return
        if not uri or not uri.startswith("http"):
            return
        if any(b.get("url") == uri for b in self.bookmarks):
            self.bookmarks = [b for b in self.bookmarks if b.get("url") != uri]
            msg = "Bookmark removed"
        else:
            self.bookmarks.append({"title": v.title() or uri, "url": uri})
            msg = "Bookmarked ★"
        _save(BOOKMARKS_FILE, self.bookmarks)
        self.refresh_bookmark_bar()
        self.refresh_chrome()
        self.status.setText(f"◈ {msg}: {uri}")

    # ---- workspaces (Opera-style; switches tab sets, reloads on switch) ----
    def _ws_data(self):
        return self.settings.setdefault("blink_ws_tabs", [{}, {}])

    def switch_workspace(self, n):
        cur = self.settings.get("blink_ws", 0)
        if n == cur:
            return
        urls = []
        for i in range(self.stack.count()):
            try:
                u = self.stack.widget(i).url().toString()
                if u.startswith("http"):
                    urls.append(u)
            except RuntimeError:
                pass
        data = self._ws_data()
        while len(data) < 2:
            data.append({})
        data[cur] = {"tabs": urls}
        self.settings["blink_ws"] = n
        save_settings(self.settings)
        while self.stack.count():
            w = self.stack.widget(0)
            self._take_tab(0)
            if w is not None:
                w.deleteLater()
        for u in data[n].get("tabs", [])[:12] or [HOME_URL]:
            self.new_tab(u)
        for i, b in enumerate(self._ws_btns):
            b.setChecked(i == n)
        self.status.setText(f"\u25c8 Workspace {['Home', 'Work'][n]}")

    def _select(self, i):
        try:
            self.tabbar.setCurrentIndex(i)
        except Exception:
            pass
        try:
            self.stack.setCurrentIndex(i)
        except Exception:
            pass

    def _on_tab_selected(self, i):
        try:
            if i is not None and 0 <= i < self.stack.count() and self.stack.currentIndex() != i:
                self.stack.setCurrentIndex(i)
        except Exception:
            pass
        self.refresh_chrome()

    def _take_tab(self, i):
        w = self.stack.widget(i)
        try:
            self.tabbar.removeTab(i)
        except Exception:
            pass
        if w is not None:
            try:
                self.stack.removeWidget(w)
            except Exception:
                pass
        return w

    # ---- tabs ----
    def close_tab_index(self, i):
        v = self.stack.widget(i)
        try:
            uri = v.url().toString() if v else ""
            if uri.startswith("http"):
                self.closed_stack.append({"title": v.title() or uri, "url": uri})
                del self.closed_stack[:-CLOSED_MAX]
        except RuntimeError:
            pass
        if self.stack.count() <= 1:
            self.close()
        else:
            self._take_tab(i)
            if v is not None:
                v.deleteLater()

    def close_current_tab(self, _a=False):
        i = self.tabbar.currentIndex()
        if i >= 0:
            self.close_tab_index(i)

    def reopen_closed(self, _a=False):
        if not self.closed_stack:
            self.status.setText("◈ Nothing to reopen")
            return
        self.new_tab(self.closed_stack.pop().get("url", HOME_URL))

    def duplicate_tab(self, _a=False):
        v = self.current_view()
        if v is not None:
            try:
                self.new_tab(v.url().toString() or HOME_URL)
            except RuntimeError:
                pass

    def close_others(self, _a=False):
        cur = self.current_view()
        for i in reversed(range(self.stack.count())):
            if self.stack.widget(i) is not cur:
                w = self.stack.widget(i)
                self._take_tab(i)
                if w is not None:
                    w.deleteLater()

    def next_tab(self, _a=False):
        n = self.stack.count()
        if n > 1:
            self._select((self.tabbar.currentIndex() + 1) % n)

    def prev_tab(self, _a=False):
        n = self.stack.count()
        if n > 1:
            self._select((self.tabbar.currentIndex() - 1) % n)

    def goto_tab(self, i):
        n = self.stack.count()
        if n:
            self._select(n - 1 if i == -1 else min(i, n - 1))

    def tab_menu(self, pos):
        m = QMenu(self)
        m.addAction("Duplicate tab", self.duplicate_tab)
        m.addAction("Copy page address", self.copy_url)
        m.addAction("Close other tabs", self.close_others)
        m.addAction("Reopen closed tab (Ctrl+Shift+T)", self.reopen_closed)
        m.addAction("New tab (Ctrl+T)", lambda _a=False: self.new_tab(HOME_URL))
        m.exec(self.tabbar.mapToGlobal(pos))

    def copy_url(self, _a=False):
        v = self.current_view()
        if v is not None:
            try:
                QApplication.clipboard().setText(v.url().toString())
            except RuntimeError:
                pass

    def show_tabs_overview(self, _a=False):
        names = []
        for i in range(self.stack.count()):
            v = self.stack.widget(i)
            try:
                names.append(f"{i + 1}. {v.title() or v.url().toString()}"[:60])
            except RuntimeError:
                names.append(f"{i + 1}. …")
        name, ok = QInputDialog.getItem(self, f"Tabs ({len(names)})",
                                        "Jump to tab:", names, 0, False)
        if ok and name in names:
            self._select(names.index(name))

    # ---- nav ----
    def go_back(self, _a=False):
        v = self.current_view()
        if v is not None:
            v.back()

    def go_fwd(self, _a=False):
        v = self.current_view()
        if v is not None:
            v.forward()

    def go_reload(self, _a=False):
        v = self.current_view()
        if v is not None:
            v.reload()

    # ---- find / zoom ----
    def find_next(self, text=None):
        v = self.current_view()
        t = self.find_entry.text() if text is None else text
        if v is not None and t:
            v.findText(t)

    def find_clear(self):
        v = self.current_view()
        if v is not None:
            try:
                v.findText("")
            except Exception:
                pass

    def zoom(self, delta):
        v = self.current_view()
        if v is not None:
            v.setZoomFactor(max(0.3, min(3.0, v.zoomFactor() + delta)))

    def zoom_reset(self, _a=False):
        v = self.current_view()
        if v is not None:
            v.setZoomFactor(1.0)

    # ---- downloads (Chrome-style manager, Ctrl+J) ----
    def on_download(self, req):
        try:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save file",
                os.path.join(os.path.expanduser("~/Downloads"),
                             req.downloadFileName() or "download"))
            if not path:
                return
            req.setDownloadDirectory(os.path.dirname(path))
            req.setDownloadFileName(os.path.basename(path))
            self.download_items.append({"name": os.path.basename(path), "req": req,
                                        "state": "…"})
            req.stateChanged.connect(lambda _s, r=req: self.download_progress(r))
            req.accept()
            self.status.setText(f"◈ Downloading {os.path.basename(path)}…")
        except Exception as e:
            self.status.setText(f"◈ Download failed: {e}")

    def download_progress(self, req):
        try:
            st = req.state()
            name = req.downloadFileName()
            for d in self.download_items:
                if d["req"] is req:
                    d["state"] = f"{req.receivedBytes() // 1024}K" if st == req.DownloadState.DownloadInProgress else "done ✓" if st == req.DownloadState.DownloadCompleted else "stopped"
            if st == req.DownloadState.DownloadCompleted:
                self.status.setText(f"◈ Downloaded {name} ✓")
        except RuntimeError:
            pass

    def show_downloads(self, _a=False):
        if not self.download_items:
            QMessageBox.information(self, "Downloads", "No downloads yet.")
            return
        lines = [f"{d['name']} — {d['state']}" for d in self.download_items[-20:]]
        QMessageBox.information(self, f"Downloads ({len(self.download_items)})", "\n".join(lines))

    # ---- dialogs ----
    def list_dialog(self, title, items, on_pick):
        names = [f"{it.get('title', '')[:40]} — {it.get('url', '')[:60]}" for it in items[-50:]][::-1]
        if not names:
            QMessageBox.information(self, title, "Nothing here yet.")
            return
        name, ok = QInputDialog.getItem(self, title, "Open:", names, 0, False)
        if ok and name in names:
            idx = names.index(name)
            on_pick(items[-50:][::-1][idx].get("url", ""))

    def show_search_engine(self, _a=False):
        names = [f"{s['name']}" for s in SEARCH_ENGINES.values()]
        keys = list(SEARCH_ENGINES)
        cur = keys.index(self.settings.get("engine", "vixzen")) if self.settings.get("engine") in keys else 0
        name, ok = QInputDialog.getItem(self, "Search engine", "Default search:",
                                        names, cur, False)
        if ok and name in names:
            self.settings["engine"] = keys[names.index(name)]
            save_settings(self.settings)
            self.refresh_chrome()

    def show_about(self, _a=False):
        QMessageBox.about(self, "About Vixzen Blink",
                          f"{APP_NAME} v{VERSION} (experimental)\n\n"
                          "Real Chromium/Blink engine via QtWebEngine.\n"
                          "Companion to Vixzen Web (lightweight default).\n"
                          "Private by default · Vixzen Search built in.")

    def app_menu(self, _a=False):
        m = QMenu(self)
        m.addAction("New tab (Ctrl+T)", lambda _a=False: self.new_tab(HOME_URL))
        m.addAction("Home (Alt+Home)", lambda _a=False: self.load_in_current(HOME_URL))
        m.addAction("All tabs… (Ctrl+Shift+A)", self.show_tabs_overview)
        m.addSeparator()
        m.addAction("Find in page… (Ctrl+F)", self.show_find)
        m.addAction("Zoom in (Ctrl++)", lambda _a=False: self.zoom(0.1))
        m.addAction("Zoom out (Ctrl+-)", lambda _a=False: self.zoom(-0.1))
        m.addAction("Reset zoom (Ctrl+0)", self.zoom_reset)
        m.addSeparator()
        m.addAction("Block trackers on this site (on/off)", lambda _a=False: self.toggle_site_block())
        m.addAction("Appearance: Chrome/Glass", lambda _a=False: self.toggle_appearance())
        m.addAction("Bookmark bar (Ctrl+Shift+B)", self.toggle_bar)
        m.addAction("Reopen closed tab (Ctrl+Shift+T)", self.reopen_closed)
        m.addAction("Duplicate tab", self.duplicate_tab)
        m.addAction("Search engine…", self.show_search_engine)
        m.addAction("Bookmarks", lambda _a=False: self.list_dialog("Bookmarks", self.bookmarks, self.load_in_current))
        m.addAction("History", lambda _a=False: self.list_dialog("History", self.history, self.load_in_current))
        m.addAction("Downloads (Ctrl+J)", self.show_downloads)
        m.addAction(f"About {APP_NAME}", self.show_about)
        m.exec(QCursor.pos())

    def show_find(self, _a=False):
        self.findbar.show()
        self.find_entry.setFocus()

    def add_shortcuts(self):
        def sc(key, fn):
            s = QShortcut(QKeySequence(key), self)
            s.setContext(Qt.ShortcutContext.ApplicationShortcut)
            s.activated.connect(fn)
        sc("Ctrl+L", lambda: (self.url.setFocus(), self.url.selectAll()))
        sc("Ctrl+T", lambda: self.new_tab(HOME_URL))
        sc("Ctrl+W", self.close_current_tab)
        sc("Ctrl+Shift+T", self.reopen_closed)
        sc("Ctrl+Shift+B", self.toggle_bar)
        sc("Ctrl+Tab", self.next_tab)
        sc("Ctrl+Shift+Tab", self.prev_tab)
        sc("Ctrl+J", self.show_downloads)
        for i in range(1, 9):
            sc(f"Ctrl+{i}", lambda _c=False, n=i - 1: self.goto_tab(n))
        sc("Ctrl+9", lambda: self.goto_tab(-1))
        sc("Ctrl+R", self.go_reload)
        sc("Ctrl+F", self.show_find)
        sc("Escape", self.findbar.hide)
        sc("Ctrl+D", self.on_bookmark)
        sc("Ctrl+Shift+A", self.show_tabs_overview)
        sc("Ctrl+Shift+1", lambda: self.switch_workspace(0))
        sc("Ctrl+Shift+2", lambda: self.switch_workspace(1))
        sc("Alt+Left", self.go_back)
        sc("Alt+Right", self.go_fwd)
        sc("Alt+Home", lambda: self.load_in_current(HOME_URL))
        sc("Ctrl+Plus", lambda: self.zoom(0.1))
        sc("Ctrl+Minus", lambda: self.zoom(-0.1))
        sc("Ctrl+0", self.zoom_reset)


if QT_BINDING == "PyQt6":
    from PyQt6.QtCore import pyqtSignal as Signal
else:
    from PySide6.QtCore import Signal


class _WorkerThread(QThread):
    finished_ok = Signal(object, int)

    def __init__(self, parent, token, fn, *args):
        super().__init__(parent)
        self._token, self._fn, self._args = token, fn, args

    def run(self):
        try:
            res = self._fn(*self._args)
        except Exception:
            res = None
        try:
            self.finished_ok.emit(res, self._token)
        except RuntimeError:
            pass


class _SearchThread(_WorkerThread):
    def __init__(self, parent, query, bookmarks, history):
        super().__init__(parent, 0, lambda: None)
        self._q = query

    def run(self):
        try:
            par = self.parent()
            res, off = VSearch.search(self._q,
                                      par.bookmarks if par else [],
                                      par.history if par else [])
        except Exception:
            res, off = [], True
        try:
            self.finished_ok.emit((res, off), 0)
        except RuntimeError:
            pass



if __name__ == "__main__":
    if "--smoke" in sys.argv:
        ensure_config()
        assert QT_BINDING in ("PyQt6", "PySide6"), QT_BINDING
        assert VSearch is not None, "vixzen_search missing"
        assert to_url("example.com") == "https://example.com"
        assert search_url("hi", "google").startswith("https://www.google.com/")
        assert to_url("vixzen:search?q=x") == "vixzen:search?q=x"
        assert "Vixzen" in start_page_html()
        assert VSearch.query_from_url("vixzen:search?q=a+b") == "a b"
        print(f"blink smoke OK v{VERSION} ({QT_BINDING}, core=web_core)")
    else:
        start = HOME_URL
        for a in sys.argv[1:]:
            if not a.startswith("-"):
                u = to_url(a)
                if u:
                    start = u
                break
        app = QApplication(sys.argv[:1])
        app.setApplicationName(APP_NAME)
        app.setOrganizationName("VixzenOS")
        win = BrowserWin(start)
        win.show()
        sys.exit(app.exec())
