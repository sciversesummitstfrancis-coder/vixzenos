"""Vixzen Tracker Blocklist v0.1 — shared by Vixzen Web (WebKit
UserContentFilter) and Vixzen Blink (QWebEngineUrlRequestInterceptor).

Design: host-based blocking. A request is blocked when its host — or any
parent domain — is on the list AND the page allows blocking (per-site
allowlist lives in settings.json as "allowed_sites").

Sources: a curated built-in set (works offline forever) merged by `--update`
with compact reputable hosts-format feeds (default: yoyo adservers ~3k),
capped at MAX_HOSTS so an 8 GB machine never chokes.

Usage:
  python3 apps/web-browser/blocklist.py --smoke     # offline unit checks
  python3 apps/web-browser/blocklist.py --update    # refresh feeds
  python3 apps/web-browser/blocklist.py --stats     # counts + freshness
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

CONFIG_DIR = os.path.expanduser("~/.config/vixzen-web")
BLOCKLIST_FILE = os.path.join(CONFIG_DIR, "blocklist.json")
MAX_HOSTS = 8000
UPDATE_TIMEOUT = 20

SOURCES = [
    "https://pgl.yoyo.org/adservers/serverlist.php?hostformat=hosts&showintro=1&mimetype=plaintext",
]

# Curated core: the trackers/ads you meet on nearly every news/shop page.
# Works offline; feeds only extend it.
DEFAULT_HOSTS = """
doubleclick.net googleadservices.com googlesyndication.com
google-analytics.com analytics.google.com googletagmanager.com googletagservices.com
googleads.g.doubleclick.net pagead2.googlesyndication.com
facebook.net connect.facebook.net pixel.facebook.com fbsbx.com
amazon-adsystem.com aax.amazon-adsystem.com amazoncloudfraction.com
criteo.com cas.criteo.com bidswitch.net
taboola.com trc.taboola.com outbrain.com widgets.outbrain.com
hotjar.com static.hotjar.com fullstory.com
mixpanel.com api.mixpanel.com segment.com cdn.segment.com amplitude.com
newrelic.com bam.nr-data.net
scorecardresearch.com quantserve.com quantcast.com
moatads.com ads.yahoo.com advertising.com mathtag.com
pubmatic.com rubiconproject.com adsrvr.org
openx.net spotxchange.com tremorhub.com
chartbeat.com moat.com Nielsen.com imrworldwide.com
demdex.net omtrdc.net 2o7.net
ads-twitter.com static.ads-twitter.com
linkedin.com ads.linkedin.com px.ads.linkedin.com
pinterest.com ads.pinterest.com
tiktok.com ads.tiktok.com analytics.tiktok.com
snapchat.com ads.snapchat.com sc-analytics.appspot.com
reddit.com ads.reddit.com events.reddit.com
adnxs.com ibsrv.com uncertainchopsticks.com
agkn.com addthis.com ojooo.com
zemanta.com zopim.com mouseflow.com luckyorange.com
crazyegg.com inspectlet.com sessioncam.com
optimizely.com appsflyer.com branch.io
kochava.com adjust.com singular.net
mopub.com inmobi.com smaato.com
vungle.com unityads.unity3d.com applovin.com
ironsrc.com supersonicads.com
adcolony.com chartboost.com tapjoy.com
fyber.com heyads.com
popads.net popcash.net adcash.com
exoclick.com hilltopads.net
propellerads.com adsterra.com
mgid.com revcontent.com
content.ad scharfmedia.net
nr-data.net
""".split()

_WS = re.compile(r"\s+")


def parse_hosts(text):
    """Parse hosts-format text into a set of bare hostnames."""
    out = set()
    for line in (text or "").splitlines():
        line = line.split("#", 1)[0].strip().lower()
        if not line:
            continue
        parts = _WS.split(line)
        # hosts lines look like "0.0.0.0 tracker.com" or just "tracker.com"
        cands = parts[1:] if parts and re.match(r"^(0\.0\.0\.0|127\.0\.0\.1|::)", parts[0]) else parts
        for c in cands:
            c = c.strip().strip(".")
            if c and c not in ("localhost", "localhost.localdomain", "local") \
                    and "/" not in c and " " not in c:
                out.add(c)
    return out


def _parent_hits(host, blocked):
    host = (host or "").lower().strip(".")
    if not host:
        return None
    if host in blocked:
        return host
    parts = host.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in blocked:
            return parent
    return None


def matches(host, blocked):
    """True if host or any parent domain is blocked."""
    return _parent_hits(host, blocked) is not None


def is_tracker_url(url, blocked):
    try:
        return matches(urllib.parse.urlparse(url).hostname or "", blocked)
    except Exception:
        return False


def load_store():
    try:
        with open(BLOCKLIST_FILE) as f:
            d = json.load(f)
            if isinstance(d, dict) and isinstance(d.get("hosts"), list):
                return d
    except Exception:
        pass
    return {"hosts": sorted(set(DEFAULT_HOSTS)), "updated": 0, "sources": ["built-in"]}


def save_store(hosts, sources):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(BLOCKLIST_FILE, "w") as f:
            json.dump({"hosts": sorted(hosts)[:MAX_HOSTS], "updated": int(time.time()),
                       "sources": sources}, f)
        return True
    except OSError:
        return False


def get_hosts():
    return set(load_store().get("hosts", []))


def update_feeds():
    """Fetch feeds, merge with built-ins, cap, save. Returns (n, ok_sources)."""
    merged = set(h.lower() for h in DEFAULT_HOSTS)
    ok = []
    for url in SOURCES:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "VixzenBlocklist/0.1"})
            with urllib.request.urlopen(req, timeout=UPDATE_TIMEOUT) as r:
                found = parse_hosts(r.read().decode("utf-8", "replace"))
            merged |= found
            ok.append(url)
        except Exception:
            continue
    merged = set(sorted(merged)[:MAX_HOSTS])
    save_store(merged, ["built-in"] + ok)
    return len(merged), ok


def compile_apple_json(hosts, allow_unless=()):
    """Apple content-blocker JSON (WebKitGTK-safe subset: NO `|` alternation,
    its compiler rejects disjunctions). Two rules per host: exact host and
    subdomains, third-party loads only, optional unless-domain allowlist."""
    rules = []
    unless = sorted({a.lower().strip(".") for a in allow_unless if a})
    for h in sorted(set(hosts)):
        h = h.lower().strip(".")
        if not h or "/" in h or " " in h:
            continue
        e = re.escape(h)
        for pat in (f"^https?://{e}[/:]", f"^https?://[^/:]*\\.{e}[/:]"):
            trig = {"url-filter": pat, "load-type": ["third-party"]}
            if unless:
                trig["unless-domain"] = unless
            rules.append({"trigger": trig, "action": {"type": "block"}})
    return json.dumps(rules)



if __name__ == "__main__":
    if "--smoke" in sys.argv:
        fx = "# comment\n0.0.0.0 tracker.example.com\n127.0.0.1 ads.test.org # trailing\nlocalhost\n"
        got = parse_hosts(fx)
        assert got == {"tracker.example.com", "ads.test.org"}, got
        bl = {"tracker.com", "ads.example.org"}
        assert matches("tracker.com", bl) and matches("sub.tracker.com", bl)
        assert matches("ads.example.org", bl)
        assert not matches("example.org", bl) and not matches("nottracker.com", bl)
        assert is_tracker_url("https://sub.tracker.com/x.js?a=1", bl)
        assert not is_tracker_url("https://example.org/", bl)
        js = compile_apple_json(["tracker.com"], allow_unless=["mysite.org"])
        rules = json.loads(js)
        assert len(rules) == 2 and all(r["action"]["type"] == "block" for r in rules)
        assert rules[0]["trigger"]["unless-domain"] == ["mysite.org"]
        assert "third-party" in rules[0]["trigger"]["load-type"]
        assert "|" not in rules[0]["trigger"]["url-filter"]  # WebKitGTK rejects disjunctions
        assert len(DEFAULT_HOSTS) >= 60, len(DEFAULT_HOSTS)
        print(f"blocklist smoke OK v0.1 ({len(DEFAULT_HOSTS)} built-in hosts)")
    elif "--update" in sys.argv:
        n, ok = update_feeds()
        print(f"blocklist: {n} hosts from {len(ok) + 1} source(s)"
              + ("" if ok else " (feeds unreachable, built-ins kept)"))
    elif "--stats" in sys.argv:
        d = load_store()
        age = int(time.time()) - d.get("updated", 0)
        print(f"hosts={len(d.get('hosts', []))} updated={age // 3600}h ago sources={d.get('sources')}")
    else:
        print(__doc__)
