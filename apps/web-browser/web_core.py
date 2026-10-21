"""Vixzen web_core — shared, toolkit-free browser logic for Vixzen Web
(GTK/WebKit) and Vixzen Blink (Qt/Chromium). NO gi/Qt imports here:
importing this module must never pull a GUI toolkit (Qt+GTK in one
process segfaults)."""

import html as htmlmod
import json
import os
import urllib.parse
import urllib.request

HOME_URL = "vixzen:home"
CONFIG_DIR = os.path.expanduser("~/.config/vixzen-web")
BOOKMARKS_FILE = os.path.join(CONFIG_DIR, "bookmarks.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
SESSION_FILE = os.path.join(CONFIG_DIR, "session.json")
HISTORY_MAX = 200
SPEED_DIAL_MAX = 8
CLOSED_MAX = 25
SEARCH_ENGINES = {
    "vixzen": {"name": "Vixzen (private)",
               "search": "vixzen:search?q={q}",
               "suggest": "local"},
    "google": {"name": "Google",
               "search": "https://www.google.com/search?q={q}",
               "suggest": "https://suggestqueries.google.com/complete/search?client=firefox&q={q}"},
    "duckduckgo": {"name": "DuckDuckGo",
                   "search": "https://duckduckgo.com/?q={q}",
                   "suggest": "https://duckduckgo.com/ac/?q={q}&type=list"},
    "bing": {"name": "Bing",
             "search": "https://www.bing.com/search?q={q}",
             "suggest": "https://api.bing.com/osjson.aspx?query={q}"},
    "brave": {"name": "Brave",
              "search": "https://search.brave.com/search?q={q}",
              "suggest": "https://search.brave.com/api/suggest?q={q}"},
}
DEFAULT_SETTINGS = {"engine": "vixzen", "bookmark_bar": True,
                                "appearance": "chrome", "effects": "balanced",
                                "welcomed": False, "allowed_sites": [],
                                "startup": "newtab", "blocking": True}


def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
            if isinstance(data, dict):
                merged = dict(DEFAULT_SETTINGS)
                merged.update({k: data[k] for k in DEFAULT_SETTINGS if k in data})
                if merged["engine"] not in SEARCH_ENGINES:
                    merged["engine"] = "vixzen"
                return merged
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(s):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(s, f, indent=2)
    except OSError:
        pass


def search_url(query, engine=None):
    eng = engine or load_settings().get("engine", "vixzen")
    tpl = SEARCH_ENGINES.get(eng, SEARCH_ENGINES["google"])["search"]
    return tpl.format(q=urllib.parse.quote_plus(query))


def fetch_suggestions(text, engine):
    """Blocking (run in a thread). Returns list[str], never raises."""
    import urllib.request
    try:
        spec = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["vixzen"])
        url = spec["suggest"].format(q=urllib.parse.quote_plus(text))
        req = urllib.request.Request(url, headers={"User-Agent": "VixzenWeb/0.4"})
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
            out = []
            for s in data[1][:8]:
                if isinstance(s, str) and s.strip():
                    out.append(s.strip())
            return out
        if isinstance(data, list):  # DDG / Brave object style
            out = []
            for item in data[:8]:
                if isinstance(item, dict) and item.get("phrase"):
                    out.append(item["phrase"])
                elif isinstance(item, str):
                    out.append(item)
            return out
    except Exception:
        pass
    return []


def ensure_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    for path, default in ((BOOKMARKS_FILE, [{"title": "DuckDuckGo", "url": "https://duckduckgo.com/"},
                                            {"title": "Fedora Docs", "url": "https://docs.fedoraproject.org/"},
                                            {"title": "GNOME", "url": "https://gnome.org/"},
                                            {"title": "Wikipedia", "url": "https://wikipedia.org/"}]),
                          (HISTORY_FILE, [])):
        if not os.path.exists(path):
            try:
                with open(path, "w") as f:
                    json.dump(default, f, indent=2)
            except OSError:
                pass


def load_json(path, default):
    try:
        with open(path) as f:
            data = json.load(f)
            return data if isinstance(data, list) else default
    except Exception:
        return default


def save_json(path, data):
    try:
        with open(path, "w") as f:
            json.dump(data[-HISTORY_MAX:], f, indent=2)
    except OSError:
        pass


try:
    from vixzen_search import parse_bang as _parse_bang
except Exception:
    _parse_bang = None


def to_url(text):
    """Omnibox: URL stays URL, bare domains get https://, else search."""
    text = (text or "").strip()
    if not text:
        return None
    if _parse_bang is not None:
        bang = _parse_bang(text)
        if bang:
            return bang
    if text in (HOME_URL, "vixzen://home"):
        return HOME_URL
    if text.startswith("vixzen:"):
        return text
    if "://" not in text and " " not in text and "." in text:
        return "https://" + text
    if "://" in text or " " not in text and "." not in text and "/" not in text:
        if "://" in text:
            return text
        return SEARCH_URL.format(q=urllib.parse.quote_plus(text))
    if "://" in text:
        return text
    return search_url(text)


def _dial_tile(title, url):
    t = htmlmod.escape((title or url)[:22])
    u = htmlmod.escape(url)
    try:
        host = urllib.parse.urlparse(url).netloc or url[:18]
    except Exception:
        host = url[:18]
    initial = htmlmod.escape((t.strip()[:1] or "•").upper())
    return (f'<a class="dial" href="{u}"><div class="thumb">{initial}</div>'
            f'<div class="cap">{t}</div><div class="host">{htmlmod.escape(host)}</div></a>')


def _wordmark():
    cols = ["#4285F4", "#EA4335", "#FBBC05", "#4285F4", "#34A853", "#EA4335"]
    return "".join(
        f"<span style='color:{c}'>{ch}</span>"
        for ch, c in zip("Vixzen", cols))


def _insane_css():
    return """<style>
@keyframes drift { 0%{transform:translate(0,0)} 50%{transform:translate(30px,-24px)} 100%{transform:translate(0,0)} }
@keyframes rise { from{opacity:0; transform:translateY(26px)} to{opacity:1; transform:none} }
@keyframes glow { 0%,100%{text-shadow:0 0 12px rgba(124,124,255,.4)} 50%{text-shadow:0 0 34px rgba(124,124,255,.9)} }
.orb{position:fixed;border-radius:999px;filter:blur(70px);opacity:.5;pointer-events:none;animation:drift 9s ease-in-out infinite}
.orb.o1{width:340px;height:340px;left:-80px;top:-60px;background:#4F46E5}
.orb.o2{width:300px;height:300px;right:-60px;top:20%;background:#06B6D4;animation-delay:-3s}
.orb.o3{width:260px;height:260px;left:30%;bottom:-100px;background:#7C7CFF;animation-delay:-6s}
h1,.logo{animation:glow 3s ease-in-out infinite}
.grid .dial,.grid .s{animation:rise .5s ease-out backwards}
.grid .dial:nth-child(2),.grid .s:nth-child(2){animation-delay:.06s}
.grid .dial:nth-child(3),.grid .s:nth-child(3){animation-delay:.12s}
.grid .dial:nth-child(4),.grid .s:nth-child(4){animation-delay:.18s}
.grid .dial:nth-child(5),.grid .s:nth-child(5){animation-delay:.24s}
.grid .dial:nth-child(6),.grid .s:nth-child(6){animation-delay:.3s}
.grid .dial:nth-child(7),.grid .s:nth-child(7){animation-delay:.36s}
.grid .dial:nth-child(8),.grid .s:nth-child(8){animation-delay:.42s}
</style><div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div>"""


def start_page_html(bookmarks=None, history=None, skin="glass", fx="balanced"):
    if skin == "chrome":
        return _chrome_home_html(bookmarks, history, fx)
    """Google-style new tab: logo, one search box, shortcut tiles. Glassy."""
    bookmarks = bookmarks or []
    history = history or []
    dials = bookmarks[:SPEED_DIAL_MAX]
    if len(dials) < 4:
        seen, freq = {d.get("url") for d in dials}, []
        for h in reversed(history):
            u = h.get("url", "")
            if u and u not in seen and u.startswith("http"):
                seen.add(u)
                freq.append(h)
            if len(dials) + len(freq) >= SPEED_DIAL_MAX:
                break
        dials = dials + freq
    if not dials:
        dials = [{"title": "Wikipedia", "url": "https://wikipedia.org/"},
                 {"title": "Fedora Docs", "url": "https://docs.fedoraproject.org/"},
                 {"title": "GNOME", "url": "https://gnome.org/"}]
    tiles = "\n".join(_dial_tile(d.get("title", ""), d.get("url", "")) for d in dials[:SPEED_DIAL_MAX])
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>New Tab — Vixzen Web</title>
<style>
body{{font-family:-apple-system,Cantarell,system-ui,sans-serif;margin:0;min-height:100vh;color:#fff;
background:radial-gradient(900px 500px at 50% 0%,rgba(79,70,229,.45),transparent 60%),
linear-gradient(180deg,#171a30,#0b0e1a);}}
.wrap{{max-width:640px;margin:0 auto;padding:12vh 20px 40px;text-align:center}}
.logo{{font-size:52px;font-weight:800;letter-spacing:-2px;margin:0}}
.logo span{{color:#a5b4ff}}.tag{{opacity:.7;margin:10px 0 26px;font-size:15px}}
form{{display:flex;gap:8px;padding:8px;border-radius:999px;
background:rgba(255,255,255,.14);-webkit-backdrop-filter:blur(24px) saturate(1.6);backdrop-filter:blur(24px) saturate(1.6);
border:1px solid rgba(255,255,255,.28);border-top-color:rgba(255,255,255,.6);
box-shadow:inset 0 1px 0 rgba(255,255,255,.4),0 16px 48px rgba(0,0,0,.4)}}
form:focus-within{{border-color:rgba(165,180,255,.9);box-shadow:inset 0 1px 0 rgba(255,255,255,.4),0 0 28px rgba(124,124,255,.55)}}
input{{flex:1;padding:14px 22px;border-radius:999px;border:0;outline:0;background:rgba(0,0,0,.28);color:#fff;font-size:16px}}
button{{padding:14px 26px;border-radius:999px;border:1px solid rgba(255,255,255,.3);border-top-color:rgba(255,255,255,.6);
background:linear-gradient(180deg,rgba(124,124,255,.95),rgba(79,70,229,.95));color:#fff;font-weight:700;font-size:15px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px;margin-top:34px}}
.dial{{padding:18px 10px;border-radius:22px;text-decoration:none;color:#fff;
background:rgba(255,255,255,.10);-webkit-backdrop-filter:blur(22px) saturate(1.6);backdrop-filter:blur(22px) saturate(1.6);
border:1px solid rgba(255,255,255,.22);border-top-color:rgba(255,255,255,.5);
box-shadow:inset 0 1px 0 rgba(255,255,255,.3),0 10px 30px rgba(0,0,0,.3)}}
.dial:hover{{background:rgba(255,255,255,.18);box-shadow:inset 0 1px 0 rgba(255,255,255,.4),0 0 24px rgba(124,124,255,.5)}}
.thumb{{width:46px;height:46px;border-radius:999px;margin:0 auto 8px;display:flex;align-items:center;justify-content:center;
font-size:20px;font-weight:800;color:#fff;background:linear-gradient(135deg,#7C7CFF,#22D3EE);
box-shadow:inset 0 1px 0 rgba(255,255,255,.5),0 4px 14px rgba(0,0,0,.3)}}
.cap{{font-weight:700;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.host{{opacity:.6;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.foot{{opacity:.45;font-size:12px;margin-top:26px}}</style></head><body>{_insane_css() if fx == "insane" else ""}<div class="wrap">
<p class="logo">◈ Vixzen</p><p class="tag">Search privately — nothing you type is logged.</p>
<form action="vixzen:search"><input name="q" placeholder="Search Vixzen or type a web address" autofocus>
<button>Search</button></form>
<div class="grid">{tiles}</div>
<div class="foot">New here? Press <b>Ctrl+L</b> to jump to the address bar anytime.</div>
</div></body></html>"""

def _chrome_home_html(bookmarks=None, history=None, fx="balanced"):
    """Google-style new tab (original wordmark, Vixzen-powered search)."""
    dials = list(bookmarks or [])[:8]
    if len(dials) < 4:
        seen = {d.get("url") for d in dials}
        for h in reversed(history or []):
            u = h.get("url", "")
            if u and u not in seen and u.startswith("http"):
                seen.add(u)
                dials.append(h)
            if len(dials) >= 8:
                break
    if not dials:
        dials = [{"title": "Wikipedia", "url": "https://wikipedia.org/"},
                 {"title": "Fedora Docs", "url": "https://docs.fedoraproject.org/"}]
    import html as _h
    import urllib.parse as _u
    tiles = []
    for d in dials[:8]:
        title, url = (d.get("title", "") or d.get("url", ""))[:20], d.get("url", "")
        try:
            host = _u.urlparse(url).netloc
        except Exception:
            host = ""
        initial = (_h.escape(title.strip()[:1] or "?")).upper()
        tiles.append(
            f"<a class='s' href='{_h.escape(url)}'><span class='c'>{initial}</span>"
            f"<span class='l'>{_h.escape(title)}</span></a>")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>New Tab</title>
<style>
body{{font-family:Roboto,Arial,sans-serif;margin:0;min-height:100vh;background:#FFFFFF;color:#202124;
display:flex;flex-direction:column;align-items:center}}
.logo{{font-size:64px;font-weight:500;letter-spacing:-3px;margin:14vh 0 28px}}
form{{display:flex;align-items:center;gap:10px;width:min(560px,86vw);padding:6px 8px 6px 20px;
border-radius:999px;background:#FFFFFF;border:1px solid #DFE1E5;
box-shadow:0 1px 6px rgba(32,33,36,.28)}}
form:focus-within{{box-shadow:0 2px 10px rgba(32,33,36,.35)}}
input{{flex:1;border:0;outline:0;font-size:16px;color:#202124;background:transparent}}
button{{border:0;background:transparent;font-size:16px;color:#5F6368;padding:8px 14px}}
.grid{{display:flex;gap:6px;margin-top:34px;flex-wrap:wrap;justify-content:center;max-width:560px}}
.s{{width:112px;padding:12px 4px;border-radius:8px;text-decoration:none;color:#202124;text-align:center}}
.s:hover{{background:#F1F3F4}}
.c{{width:48px;height:48px;border-radius:999px;margin:0 auto 8px;display:flex;align-items:center;
justify-content:center;font-size:20px;color:#FFFFFF;background:#8AB4F8}}
.l{{font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}}
.foot{{margin-top:auto;padding:16px;font-size:12px;color:#70757A}}</style></head><body>{_insane_css() if fx == "insane" else ""}
<p class="logo">{_wordmark()}</p>
<form action="vixzen:search"><span style="color:#9AA0A6">🔍</span>
<input name="q" placeholder="Search Vixzen or type a URL" autofocus><button>➤</button></form>
<div class="grid">{"".join(tiles)}</div>
<div class="foot">Vixzen Search · private · no log</div>
</body></html>"""
