"""Chrome/Firefox importer for Vixzen Web — one-click onboarding.

Reads the other browsers' bookmark + history stores (read-only; history via
a temp SQLite copy so a running Chrome's lock never bites us) and returns
plain [{title, url}] lists the caller merges + dedupes.

  python3 apps/web-browser/chrome_import.py --smoke    # fixtures, offline
  python3 apps/web-browser/chrome_import.py --scan     # profiles on this machine
"""
import json
import os
import shutil
import sqlite3
import sys
import tempfile

BOOKMARK_LIMIT = 2000
HISTORY_LIMIT = 500


def chrome_profile_dirs():
    out = []
    for base in ("~/.config/google-chrome", "~/.config/chromium"):
        b = os.path.expanduser(base)
        for name in ("Default", "Profile 1"):
            d = os.path.join(b, name)
            if os.path.isdir(d):
                out.append(("chrome", d))
    return out


def firefox_profile_dirs():
    out = []
    base = os.path.expanduser("~/.mozilla/firefox")
    try:
        names = os.listdir(base)
    except OSError:
        return out
    for n in names:
        d = os.path.join(base, n)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, "places.sqlite")):
            out.append(("firefox", d))
    return out


def find_profiles():
    return chrome_profile_dirs() + firefox_profile_dirs()


def _walk_chrome_nodes(nodes, out):
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        if node.get("type") == "url" and (node.get("url") or "").startswith("http"):
            out.append({"title": node.get("name") or node["url"], "url": node["url"]})
        _walk_chrome_nodes(node.get("children"), out)
        if len(out) >= BOOKMARK_LIMIT:
            break


def read_chrome_bookmarks(profile_dir):
    try:
        with open(os.path.join(profile_dir, "Bookmarks")) as f:
            data = json.load(f)
    except Exception:
        return []
    out = []
    for root in (data.get("roots") or {}).values():
        if isinstance(root, dict):
            _walk_chrome_nodes(root.get("children"), out)
    return out[:BOOKMARK_LIMIT]


def _query_copy(db_path, sql, limit):
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmp.close()
        shutil.copy2(db_path, tmp.name)
    except Exception:
        return []
    out = []
    try:
        con = sqlite3.connect(f"file:{tmp.name}?mode=ro", uri=True, timeout=5)
        cur = con.execute(sql, (limit,))
        for title, url in cur.fetchall():
            if url and url.startswith("http"):
                out.append({"title": title or url, "url": url})
        con.close()
    except Exception:
        pass
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    return out


def read_chrome_history(profile_dir):
    return _query_copy(os.path.join(profile_dir, "History"),
                       "SELECT title, url FROM urls ORDER BY last_visit_time DESC LIMIT ?",
                       HISTORY_LIMIT)


def read_firefox_bookmarks(profile_dir):
    return _query_copy(os.path.join(profile_dir, "places.sqlite"),
                       """SELECT p.title, p.url FROM moz_places p
                          JOIN moz_bookmarks b ON b.fk = p.id
                          WHERE b.type = 1 AND p.url LIKE 'http%'
                          ORDER BY b.dateAdded DESC LIMIT ?""",
                       BOOKMARK_LIMIT)


def read_firefox_history(profile_dir):
    return _query_copy(os.path.join(profile_dir, "places.sqlite"),
                       """SELECT p.title, p.url FROM moz_places p
                          JOIN moz_historyvisits v ON v.place_id = p.id
                          WHERE p.url LIKE 'http%'
                          GROUP BY p.id ORDER BY MAX(v.visit_date) DESC LIMIT ?""",
                       HISTORY_LIMIT)


def import_all():
    """(bookmarks, history) merged across every profile found."""
    bm, hi = [], []
    for kind, d in find_profiles():
        if kind == "chrome":
            bm += read_chrome_bookmarks(d)
            hi += read_chrome_history(d)
        else:
            bm += read_firefox_bookmarks(d)
            hi += read_firefox_history(d)
    return bm[:BOOKMARK_LIMIT], hi[:HISTORY_LIMIT]


if __name__ == "__main__":
    if "--smoke" in sys.argv:
        import pathlib
        t = pathlib.Path("/tmp/opencode/chrome-fixture")
        (t / "Default").mkdir(parents=True, exist_ok=True)
        (t / "Default" / "Bookmarks").write_text(json.dumps({
            "roots": {"bookmark_bar": {"children": [
                {"type": "url", "name": "Example", "url": "https://example.com/"},
                {"type": "folder", "name": "F", "children": [
                    {"type": "url", "name": "Wiki", "url": "https://wikipedia.org/"}]},
            ]}}}))
        con = sqlite3.connect(t / "Default" / "History")
        con.execute("DROP TABLE IF EXISTS urls")
        con.execute("CREATE TABLE urls (title TEXT, url TEXT, last_visit_time INT)")
        con.execute("INSERT INTO urls VALUES ('Example','https://example.com/',13200000000000000)")
        con.commit()
        con.close()
        bm = read_chrome_bookmarks(str(t / "Default"))
        assert len(bm) == 2 and bm[0]["url"] == "https://example.com/", bm
        hi = read_chrome_history(str(t / "Default"))
        assert hi and hi[0]["url"] == "https://example.com/", hi
        print("chrome-import smoke OK v0.1")
    elif "--scan" in sys.argv:
        for kind, d in find_profiles():
            print(f"{kind}: {d}")
        if not find_profiles():
            print("no chrome/firefox profiles found")
    else:
        bm, hi = import_all()
        print(f"{len(bm)} bookmarks, {len(hi)} history entries")
