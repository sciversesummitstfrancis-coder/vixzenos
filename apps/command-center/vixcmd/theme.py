"""Vixzen theme/accent/glass readers (no changes, ever)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "..", "preview", "src"))
try:
    from design import ACCENTS, PERF_MODES
except Exception:
    ACCENTS, PERF_MODES = {}, ()


def theme_list(as_json=False):
    names = list(ACCENTS) if ACCENTS else ["Vixzen Indigo"]
    if as_json:
        print(json.dumps({"themes": names}))
    else:
        print("Vixzen themes (use Settings to apply):")
        for n in names:
            print(f"  • {n}")
    return 0


GLASS_MAP = {"saver": "Lite", "balanced": "Balanced",
             "enhanced": "Glass", "insane": "Glass"}


def glass_status(as_json=False):
    cfg = os.path.expanduser("~/.config/vixzen/settings.json")
    perf = "balanced"
    try:
        perf = json.load(open(cfg)).get("perf", "balanced")
    except Exception:
        pass
    tier = GLASS_MAP.get(perf, "Balanced")
    if as_json:
        print(json.dumps({"perf": perf, "glass": tier}))
    else:
        print(f"Glass tier: {tier}  (perf mode: {perf})")
        print("Change it in Vixzen Settings → Performance.")
    return 0
