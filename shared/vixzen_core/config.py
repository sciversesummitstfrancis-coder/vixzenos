"""Vixzen shared config: per-app JSON settings under ~/.config/vixzen/.

One load/save implementation for every Vixzen app (replaces five copies).
Pure stdlib — safe to import anywhere, including tests.
"""
import json
import os

BASE = os.path.join(os.path.expanduser("~"), ".config", "vixzen")


def path(app):
    """Config file path for an app id like 'settings' or 'preview'."""
    return os.path.join(BASE, f"{app}.json")


def load(app, defaults):
    """Load config merged over defaults. Never raises; corrupt files yield
    defaults (backed up once beside the original)."""
    cfg = dict(defaults)
    p = path(app)
    try:
        with open(p) as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update(data)
    except FileNotFoundError:
        pass
    except Exception:
        try:
            os.replace(p, p + ".corrupt-bak")
        except OSError:
            pass
    return cfg


def save(app, cfg):
    """Persist config atomically. Never raises."""
    p = path(app)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".tmp"
        with open(tmp, "w") as f:
            json.dump(cfg, f)
        os.replace(tmp, p)
    except OSError:
        pass
