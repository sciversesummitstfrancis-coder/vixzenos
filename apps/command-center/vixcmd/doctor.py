"""Vixzen doctor: read-only health checks with recommendations.

Exit codes: 0 healthy, 1 warnings only, 2 problems found.
Never repairs anything; prints what a human (or admin) should do.
"""
import os
import re
import shutil
import subprocess


def _run(cmd, timeout=8):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip()
    except Exception as e:
        return 127, str(e)


def _mem():
    try:
        with open("/proc/meminfo") as f:
            txt = f.read()
        total = int(re.search(r"MemTotal:\s*(\d+)", txt).group(1)) // 1024
        avail = int(re.search(r"MemAvailable:\s*(\d+)", txt).group(1)) // 1024
        return total, avail
    except Exception:
        return 0, 0


def _disk_use(path="/"):
    try:
        st = os.statvfs(path)
        used = 100 * (1 - st.f_bavail / st.f_blocks)
        return used
    except OSError:
        return -1.0


CHECKS = []


def check(name):
    def deco(fn):
        CHECKS.append((name, fn))
        return fn
    return deco


@check("memory")
def _c_mem(full):
    total, avail = _mem()
    if total == 0:
        return ("unknown", "could not read /proc/meminfo")
    if total < 3500:
        return ("warn", f"only {total} MB RAM; prefer Vixzen Lite mode "
                        "(Saver perf, animations off)")
    if avail < 500:
        return ("warn", f"only {avail} MB available; close heavy apps")
    return ("ok", f"{total} MB total, {avail} MB available")


@check("cpu")
def _c_cpu(full):
    try:
        n = os.cpu_count() or 0
    except Exception:
        n = 0
    if n <= 2:
        return ("warn", f"{n} CPUs; keep effects on Balanced or Saver")
    return ("ok", f"{n} CPUs")


@check("storage")
def _c_storage(full):
    use = _disk_use("/")
    if use < 0:
        return ("unknown", "could not stat /")
    if use > 90:
        return ("bad", f"/ is {use:.0f}% full; free space or the live "
                       "session may fail")
    if use > 80:
        return ("warn", f"/ is {use:.0f}% full; consider cleaning up")
    return ("ok", f"/ is {use:.0f}% full")


@check("graphics")
def _c_graphics(full):
    rc, out = _run(["lspci"])
    if rc != 0 or not out:
        return ("unknown", "lspci unavailable")
    low = "intel" in out.lower() and ("HD Graphics" in out or "UHD" in out)
    if low:
        return ("warn", "integrated Intel graphics; avoid Enhanced/insane "
                         "effects (Balanced is the sweet spot)")
    return ("ok", "discrete or modern graphics detected")


@check("audio")
def _c_audio(full):
    if shutil.which("pactl") is None and shutil.which("wpctl") is None:
        return ("warn", "no PulseAudio/PipeWire client found")
    rc, out = _run(["wpctl", "status"])
    if rc == 0 and "Audio" in out:
        return ("ok", "PipeWire audio stack present")
    rc, out = _run(["pactl", "info"])
    if rc == 0:
        return ("ok", "audio server reachable")
    return ("warn", "audio stack not responding; try: vix repair audio "
                     "(when implemented)")


@check("network")
def _c_network(full):
    rc, out = _run(["nmcli", "-t", "-f", "STATE", "general"])
    out = out.strip().lower()
    if "connected" in out:
        return ("ok", "network connected")
    return ("warn", "no connection; check cable/Wi-Fi or run the "
                     "Network quick control")


@check("session")
def _c_session(full):
    sess = os.environ.get("XDG_SESSION_TYPE", "unknown")
    if sess == "wayland":
        return ("ok", "Wayland session")
    if sess == "x11":
        return ("warn", "X11 session; Vixzen targets Wayland")
    return ("unknown", "no graphical session detected "
                       "(run inside GNOME to check shell state)")


@check("services")
def _c_services(full):
    rc, out = _run(["systemctl", "--failed", "--no-legend"])
    if rc != 0:
        return ("unknown", "systemctl unavailable (not systemd boot?)")
    if not out.strip():
        return ("ok", "no failed services")
    lines = [l for l in out.splitlines() if l.strip()]
    return ("bad", f"{len(lines)} failed service(s): " +
                   ", ".join(l.split()[0] for l in lines[:3]) +
                   " — inspect with: systemctl status <name>")


def _updates(full):
    if not full:
        return None
    if shutil.which("dnf") is None:
        return ("unknown", "dnf unavailable")
    rc, out = _run(["dnf", "check-update", "-q"], timeout=120)
    if rc == 0:
        return ("ok", "no pending updates")
    if rc == 100:
        n = len([l for l in out.splitlines() if l.strip()])
        return ("warn", f"{n} update(s) pending; review before applying")
    return ("unknown", "update check failed (offline?)")


def run(full=False, as_json=False):
    results = []
    for name, fn in CHECKS:
        try:
            level, msg = fn(full)
        except Exception as e:
            level, msg = "unknown", f"check crashed: {e}"
        results.append((name, level, msg))
    extra = _updates(full)
    if extra is not None:
        results.append(("updates", *extra))
    worst = 0
    rank = {"ok": 0, "unknown": 0, "warn": 1, "bad": 2}
    for _, level, _ in results:
        worst = max(worst, rank.get(level, 0))
    if as_json:
        import json
        print(json.dumps({"overall": ["GOOD", "FAIR", "POOR"][worst],
                          "checks": [{"name": n, "level": l, "detail": m}
                                     for n, l, m in results]}, indent=2))
    else:
        mark = {"ok": "✓", "warn": "⚠", "bad": "✗", "unknown": "?"}
        print("Vixzen Doctor")
        for name, level, msg in results:
            print(f"  {mark.get(level, '?')} {name:10} {msg}")
        print(f"\nOverall health: {['GOOD', 'FAIR', 'POOR'][worst]}")
        if worst > 0:
            print("Nothing was changed. Fix suggestions are printed above.")
    return worst
