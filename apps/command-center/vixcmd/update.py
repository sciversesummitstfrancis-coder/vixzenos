"""Vixzen update client — check the VixzenOS channel for new releases."""
import os
import shutil
import subprocess

REPO_ID = "vixzenos"


def _dnf(args, timeout=120):
    if shutil.which("dnf") is None:
        return None, "dnf not available"
    try:
        r = subprocess.run(["dnf"] + args, capture_output=True, text=True,
                           timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except Exception as e:
        return 1, str(e)


def channel_enabled():
    rc, out = _dnf(["--quiet", "repolist", "--enabled"], timeout=60)
    if rc is None:
        return False
    return REPO_ID in out.lower()


def check(as_json=False):
    """Report VixzenOS package updates available in the channel."""
    if not channel_enabled():
        msg = ("VixzenOS channel not enabled. Enable it with: "
               "sudo vixzen-repo-setup.sh")
        if as_json:
            import json
            print(json.dumps({"channel": False, "message": msg}))
        else:
            print("Vixzen Update")
            print(f"  ⚠ {msg}")
        return 1
    rc, out = _dnf(["--quiet", "check-update", "vixzenos-*"], timeout=300)
    if rc is None:
        msg = out
        pending = []
    elif rc == 0:
        msg, pending = "up to date", []
    elif rc == 100:
        pending = [l for l in out.splitlines() if l.strip()
                   and not l.startswith(" ")]
        msg = f"{len(pending)} update(s) available"
    else:
        msg, pending = out.strip().splitlines()[0] if out.strip() else "check failed", []
    if as_json:
        import json
        print(json.dumps({"channel": True, "message": msg,
                          "updates": pending}, indent=2))
    else:
        print("Vixzen Update")
        print(f"  {msg}")
        for p in pending[:10]:
            print(f"    • {p}")
        if pending:
            print("\nApply with: sudo dnf upgrade")
    return 0 if not pending else 2


def history(as_json=False):
    """Show what was installed and when (rpm query, not dnf)."""
    if shutil.which("rpm") is None:
        rows = ["  (rpm not available)"]
    else:
        try:
            r = subprocess.run(
                ["rpm", "-qa", "vixzenos-*", "--qf",
                 "%{NAME}-%{VERSION}-%{RELEASE}  %{INSTALLTIME:date}"],
                capture_output=True, text=True, timeout=60)
            rows = [l for l in r.stdout.splitlines() if l.strip()]
        except Exception as e:
            rows = [f"  (query failed: {e})"]
    if as_json:
        import json
        print(json.dumps({"installed": rows}, indent=2))
    else:
        print("Vixzen Update History")
        for r in rows or ["  (no vixzenos packages installed)"]:
            print(f"  {r}")
    return 0
