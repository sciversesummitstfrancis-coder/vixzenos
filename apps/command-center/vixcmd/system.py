"""Vixzen command modules: system info/status (read-only facts)."""
import os
import re
import subprocess


def _run(cmd, timeout=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:
        return ""


def _release():
    for p in ("/etc/vixzen-release", "/etc/os-release"):
        if os.path.isfile(p):
            try:
                return open(p).read().strip()
            except OSError:
                pass
    return "unknown"


def info(as_json=False):
    data = {
        "os": _release().splitlines()[0] if _release() != "unknown" else "unknown",
        "kernel": _run(["uname", "-r"]),
        "cpu": "",
        "mem_total": "",
        "disk_root": "",
        "gpu": "",
        "session": os.environ.get("XDG_SESSION_TYPE", "unknown"),
        "shell": _run(["gnome-shell", "--version"]),
    }
    cpu = _run(["lscpu"])
    m = re.search(r"Model name:\s*(.+)", cpu)
    data["cpu"] = m.group(1).strip() if m else "unknown"
    mem = _run(["free", "-h"])
    m = re.search(r"Mem:\s*(\S+)", mem)
    data["mem_total"] = m.group(1) if m else "unknown"
    df = _run(["df", "-h", "/"])
    lines = df.splitlines()
    data["disk_root"] = lines[-1] if len(lines) > 1 else "unknown"
    lspci = _run(["lspci"])
    gpus = [l.split(":", 2)[-1].strip() for l in lspci.splitlines()
            if "VGA" in l or "3D controller" in l]
    data["gpu"] = "; ".join(gpus) if gpus else "unknown"
    if as_json:
        import json
        print(json.dumps(data, indent=2))
    else:
        print("Vixzen System")
        for k in ("os", "kernel", "cpu", "mem_total", "disk_root",
                  "gpu", "session", "shell"):
            print(f"  {k:10} {data[k]}")
    return 0


def status(as_json=False):
    up = _run(["uptime", "-p"]) or _run(["uptime"])
    load = ""
    try:
        load = f"{os.getloadavg()[0]:.2f}"
    except OSError:
        pass
    mem = _run(["free", "-m"])
    m = re.search(r"Mem:\s*\d+\s+(\d+)\s+\d+", mem)
    mem_used = m.group(1) + " MB" if m else "unknown"
    df = _run(["df", "-h", "/"])
    use = ""
    m = re.search(r"(\d+%)", df)
    use = m.group(1) if m else "unknown"
    data = {"uptime": up, "load_1m": load, "mem_used": mem_used,
            "disk_use": use}
    if as_json:
        import json
        print(json.dumps(data, indent=2))
    else:
        print("Vixzen Status")
        for k, v in data.items():
            print(f"  {k:10} {v}")
    return 0
