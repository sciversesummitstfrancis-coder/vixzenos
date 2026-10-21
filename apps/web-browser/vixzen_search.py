"""Vixzen Search v0.2 — our own private metasearch engine.

Honest scope: this is NOT a Google-scale crawler (that needs 100k+ servers).
It IS our own search frontend + result merger that runs inside Vixzen Web:
  1. local-first: your bookmarks + history match instantly, offline, no tracking
  2. Wikipedia opensearch for factual queries
  3. DuckDuckGo html endpoint for broad web coverage (no JS, no cookies stored)
Results merge, dedupe, and render in a Liquid Glass page. Nothing is logged
anywhere — the query only goes to the upstream sources needed, same as if
you'd visited them, minus their trackers (no cookies/JS run here).

URLs look like: vixzen:search?q=photosynthesis
"""
import html as htmlmod
import json
import re
import urllib.parse
import urllib.request

UA = {"User-Agent": "VixzenSearch/0.2 (private metasearch; no tracking)"}
TIMEOUT = 8
MAX_RESULTS = 20
WEB_RESULTS = 15

# DuckDuckGo html result links look like:
#   <a class="result__a" href="//duckduckgo.com/l/?uddg=<urlencoded>&rut=...">Title</a>
_DDG_LINK = re.compile(
    r'class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>', re.S)
_DDG_SNIP = re.compile(r'class="result__snippet"[^>]*>(?P<snip>.*?)</', re.S)
_TAG = re.compile(r"<[^>]+>")


def _clean(s):
    return htmlmod.unescape(_TAG.sub("", s or "")).strip()


def _unwrap_ddg(href):
    """Turn /l/?uddg=<enc>... into the real URL; pass through http(s) hrefs."""
    href = htmlmod.unescape(href or "")
    if href.startswith("//"):
        href = "https:" + href
    try:
        q = urllib.parse.urlparse(href).query
        params = urllib.parse.parse_qs(q)
        if "uddg" in params and params["uddg"]:
            return params["uddg"][0]
    except Exception:
        pass
    return href


def parse_ddg_html(page):
    """Parse DDG html endpoint into [{title, url, snippet}]. Pure function."""
    links = list(_DDG_LINK.finditer(page or ""))
    snips = [_clean(m.group("snip")) for m in _DDG_SNIP.finditer(page or "")]
    out = []
    for i, m in enumerate(links):
        url = _unwrap_ddg(m.group("href"))
        if not url.startswith("http"):
            continue
        title = _clean(m.group("title")) or url
        out.append({"title": title, "url": url,
                    "snippet": snips[i] if i < len(snips) else "",
                    "source": "web"})
        if len(out) >= MAX_RESULTS:
            break
    return out


_LITE_LINK = re.compile(
    r'<a[^>]*href="(?P<href>[^"]*uddg=(?P<enc>[^&"]+)[^"]*)"[^>]*>(?P<title>.*?)</a>', re.S)
_LITE_SNIP = re.compile(
    r"class=[\"']result-snippet[\"'][^>]*>(?P<snip>.*?)</td>", re.S)


def parse_ddg_lite(page):
    """Fallback parser for lite.duckduckgo.com. Pure function."""
    links = list(_LITE_LINK.finditer(page or ""))
    snips = [_clean(m.group("snip")) for m in _LITE_SNIP.finditer(page or "")]
    out = []
    for i, m in enumerate(links):
        try:
            url = urllib.parse.unquote(m.group("enc"))
        except Exception:
            continue
        if not url.startswith("http"):
            continue
        title = _clean(m.group("title")) or url
        if "duckduckgo.com" in (urllib.parse.urlparse(url).hostname or ""):
            continue
        out.append({"title": title, "url": url,
                    "snippet": snips[i] if i < len(snips) else "",
                    "source": "web"})
        if len(out) >= MAX_RESULTS:
            break
    return out


def parse_wiki_opensearch(data):
    """Parse Wikipedia opensearch JSON into result dicts. Pure function."""
    try:
        titles, descs, urls = data[1], data[2], data[3]
    except Exception:
        return []
    out = []
    for t, d, u in zip(titles, descs, urls):
        if u and u.startswith("http"):
            out.append({"title": str(t), "url": str(u),
                        "snippet": str(d or ""), "source": "wikipedia"})
    return out[:5]


def _norm(u):
    try:
        p = urllib.parse.urlparse(u.lower())
        return p.netloc.lstrip("www.") + p.path.rstrip("/")
    except Exception:
        return u.lower()


def merge_results(*lists):
    seen, out = {}, []
    for lst in lists:
        for r in lst or []:
            key = _norm(r.get("url", ""))
            if not key:
                continue
            if key not in seen:
                seen[key] = len(out)
                out.append(r)
            elif not out[seen[key]].get("snippet") and r.get("snippet"):
                out[seen[key]] = r  # snippet-bearing dupe wins
            if len(out) >= MAX_RESULTS:
                return out
    return out


BANGS = {
    "!w": "https://en.wikipedia.org/w/index.php?search={q}",
    "!wiki": "https://en.wikipedia.org/w/index.php?search={q}",
    "!g": "https://www.google.com/search?q={q}",
    "!b": "https://www.bing.com/search?q={q}",
    "!ddg": "https://duckduckgo.com/?q={q}",
    "!br": "https://search.brave.com/search?q={q}",
    "!yt": "https://www.youtube.com/results?search_query={q}",
    "!gh": "https://github.com/search?q={q}&type=repositories",
    "!so": "https://stackoverflow.com/search?q={q}",
    "!am": "https://www.amazon.com/s?k={q}",
    "!eb": "https://www.ebay.com/sch/i.html?_nkw={q}",
    "!m": "https://www.openstreetmap.org/search?query={q}",
}


def parse_bang(query):
    """!yt cats -> direct search URL. Returns None when no bang present."""
    q = (query or "").strip()
    if not q.startswith("!"):
        return None
    parts = q.split(None, 1)
    tpl = BANGS.get(parts[0].lower())
    if not tpl:
        return None
    return tpl.format(q=urllib.parse.quote_plus(parts[1] if len(parts) > 1 else ""))


def local_search(query, bookmarks, history, limit=3):
    """Offline prefix/substring match over bookmarks + history."""
    q = (query or "").lower().strip()
    if not q:
        return []
    out = []
    for pool, src in ((bookmarks, "bookmark"), (history, "history")):
        for item in pool or []:
            hay = f"{item.get('title', '')} {item.get('url', '')}".lower()
            if q in hay:
                out.append({"title": item.get("title") or item.get("url", ""),
                            "url": item.get("url", ""),
                            "snippet": f"From your {src}s", "source": src})
                if len(out) >= limit:
                    return out
    return out


def local_suggest(text, bookmarks, history, limit=8):
    q = (text or "").lower().strip()
    if len(q) < 2:
        return []
    sug, seen = [], set()
    for pool in (bookmarks or [], reversed(history or [])):
        for item in pool:
            title = item.get("title", "")
            if q in title.lower() and title.lower() not in seen:
                seen.add(title.lower())
                sug.append(title)
            if len(sug) >= limit:
                return sug
    return sug


def _fetch(url, timeout=TIMEOUT):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def search(query, bookmarks=None, history=None):
    """Full search. Returns (results, offline: bool). Never raises."""
    q = (query or "").strip()
    if not q:
        return [], False
    local = local_search(q, bookmarks, history)
    wiki, ddg, offline = [], [], False
    try:
        wurl = ("https://en.wikipedia.org/w/api.php?action=opensearch&search="
                + urllib.parse.quote_plus(q) + "&limit=5&format=json")
        wiki = parse_wiki_opensearch(json.loads(_fetch(wurl)))
    except Exception:
        offline = True
    try:
        durl = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote_plus(q)
        ddg = parse_ddg_html(_fetch(durl))
    except Exception:
        offline = True
    lite = []
    if len([r for r in ddg if r.get("snippet")]) < 4:
        try:
            lurl = "https://lite.duckduckgo.com/lite/?q=" + urllib.parse.quote_plus(q)
            lite = parse_ddg_lite(_fetch(lurl))
        except Exception:
            offline = True if not ddg else offline
    results = merge_results(local, wiki, ddg, lite)
    if not results:
        offline = True
    return results, offline


def _tile(r):
    t = htmlmod.escape(r.get("title", "") or r.get("url", ""))[:90]
    u = htmlmod.escape(r.get("url", ""))
    s = htmlmod.escape(r.get("snippet", ""))[:220]
    src = htmlmod.escape(r.get("source", "web"))
    try:
        host = urllib.parse.urlparse(r.get("url", "")).netloc
    except Exception:
        host = ""
    return (f'<a class="r" href="{u}"><div class="t">{t}</div>'
            f'<div class="u">{htmlmod.escape(host)} · {src}</div>'
            + (f'<div class="s">{s}</div>' if s else "") + "</a>")


def results_page_html(query, results, offline=False, version="0.5"):
    q = htmlmod.escape(query or "")
    if results:
        body = "\n".join(_tile(r) for r in results)
        head = f"<div class='n'>{len(results)} result{'s' if len(results) != 1 else ''} · private, no log</div>"
    elif offline:
        body = ("<div class='empty'>You're offline — showing what we can.<br>"
                "Check your connection, or try your bookmarks below.</div>")
        head = "<div class='n'>no connection</div>"
    else:
        body = f"<div class='empty'>No results for “{q}”.</div>"
        head = "<div class='n'>0 results</div>"
    fall = ("<div class='fall'>Try elsewhere: "
            f"<a href='https://www.google.com/search?q={urllib.parse.quote_plus(query or '')}'>Google</a> · "
            f"<a href='https://duckduckgo.com/?q={urllib.parse.quote_plus(query or '')}'>DuckDuckGo</a> · "
            f"<a href='https://search.brave.com/search?q={urllib.parse.quote_plus(query or '')}'>Brave</a></div>")
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Vixzen Search: {q}</title>
<style>
body{{font-family:-apple-system,Cantarell,system-ui,sans-serif;margin:0;min-height:100vh;color:#fff;
background:radial-gradient(900px 500px at 15% 0%,rgba(79,70,229,.5),transparent 60%),
radial-gradient(800px 500px at 90% 15%,rgba(6,182,212,.35),transparent 60%),
linear-gradient(160deg,#14172b,#0b0e1a);}}
.wrap{{max-width:720px;margin:0 auto;padding:36px 18px 60px}}
.brand{{font-weight:800;font-size:15px;opacity:.85}}.brand span{{color:#a5b4ff}}
form{{display:flex;gap:8px;margin:12px 0 6px;padding:8px;border-radius:999px;
background:rgba(255,255,255,.12);-webkit-backdrop-filter:blur(24px) saturate(1.6);backdrop-filter:blur(24px) saturate(1.6);
border:1px solid rgba(255,255,255,.25);border-top-color:rgba(255,255,255,.55);
box-shadow:inset 0 1px 0 rgba(255,255,255,.35),0 12px 40px rgba(0,0,0,.35)}}
input{{flex:1;padding:11px 18px;border-radius:999px;border:0;outline:0;background:rgba(0,0,0,.25);color:#fff;font-size:15px}}
button{{padding:11px 20px;border-radius:999px;border:1px solid rgba(255,255,255,.3);border-top-color:rgba(255,255,255,.6);
background:linear-gradient(180deg,rgba(124,124,255,.9),rgba(79,70,229,.9));color:#fff;font-weight:700}}
.n{{opacity:.6;font-size:13px;margin:10px 2px}}.r{{display:block;margin:10px 0;padding:16px 18px;border-radius:18px;
text-decoration:none;color:#fff;background:rgba(255,255,255,.09);
-webkit-backdrop-filter:blur(20px) saturate(1.5);backdrop-filter:blur(20px) saturate(1.5);
border:1px solid rgba(255,255,255,.2);border-top-color:rgba(255,255,255,.45);
box-shadow:inset 0 1px 0 rgba(255,255,255,.25)}}
.r:hover{{background:rgba(255,255,255,.15);box-shadow:inset 0 1px 0 rgba(255,255,255,.35),0 0 22px rgba(124,124,255,.45)}}
.t{{font-weight:700;font-size:16px}}.u{{opacity:.6;font-size:12px;margin:3px 0}}.s{{opacity:.85;font-size:14px}}
.empty{{padding:40px;text-align:center;opacity:.75}}.fall{{margin-top:18px;opacity:.7;font-size:13px}}
.fall a,.r{{color:#fff}}.fall a{{color:#a5b4ff}}</style></head><body><div class="wrap">
<div class="brand">◈ Vixzen <span>Search</span></div>
<form action="vixzen:search"><input name="q" value="{q}" placeholder="Search privately…">
<button>Go</button></form>{head}{body}{fall}
<div class="n">Vixzen Search v{version} · metasearch, zero logging</div>
</div></body></html>"""


def query_from_url(url):
    try:
        q = urllib.parse.urlparse(url).query
        return urllib.parse.parse_qs(q).get("q", [""])[0]
    except Exception:
        return ""


if __name__ == "__main__":
    import sys
    q = " ".join(a for a in sys.argv[1:] if not a.startswith("-")) or "VixzenOS"
    if "--smoke" in sys.argv:
        fx = ('<a class="result__a" href="//duckduckgo.com/l/?uddg='
              'https%3A%2F%2Fexample.com%2F&amp;rut=abc"><b>Example</b> Site</a>'
              '<a class="result__snippet">demo snippet</a>')
        r = parse_ddg_html(fx)
        assert r and r[0]["url"] == "https://example.com/", r
        w = parse_wiki_opensearch(["q", ["T"], ["D"], ["https://en.wikipedia.org/wiki/T"]])
        assert w and w[0]["source"] == "wikipedia"
        m = merge_results([{"url": "https://example.com", "title": "a"}],
                          [{"url": "https://example.com/", "title": "b"}])
        assert len(m) == 1, m
        assert local_suggest("wikip", [{"title": "Wikipedia", "url": "https://wikipedia.org"}], [])
        lx = ('<a rel="nofollow" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Flite.example%2F&amp;rut=x">Lite Ex</a>'
              "<td class='result-snippet'>lite snip here</td>")
        lr = parse_ddg_lite(lx)
        assert lr and lr[0]["url"] == "https://lite.example/" and lr[0]["snippet"] == "lite snip here", lr
        assert parse_bang("!w paris") == "https://en.wikipedia.org/w/index.php?search=paris"
        assert parse_bang("!g cats") == "https://www.google.com/search?q=cats"
        assert parse_bang("no bang here") is None and parse_bang("!nope x") is None
        m2 = merge_results([{"url": "https://example.com/", "title": "a", "snippet": ""}],
                           [{"url": "https://example.com/", "title": "a", "snippet": "SNIP"}])
        assert len(m2) == 1 and m2[0]["snippet"] == "SNIP", m2
        assert "Vixzen" in results_page_html("x", [], True)
        assert query_from_url("vixzen:search?q=hello+world") == "hello world"
        print("vixzen-search smoke OK v0.2")
    else:
        res, off = search(q)
        print(f"{len(res)} results (offline={off}) for {q!r}")
        for r in res[:10]:
            print(f"- {r['title'][:60]} | {r['url'][:80]}")
