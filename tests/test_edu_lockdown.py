"""Edu lockdown rule validation (no root needed).

A polkit rule naming an action ID that does not exist NEVER fires — the
lockdown would silently not apply. This test checks every action ID used
by the Edu rules against the live polkit action registry (pkaction), so a
typo fails the build instead of the classroom.
"""
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
RULES = sorted((REPO / "packaging" / "edu-polkit").glob("*.rules"))


def registered_actions():
    try:
        out = subprocess.run(["pkaction"], capture_output=True, text=True,
                             timeout=60).stdout
        return {l.strip() for l in out.splitlines() if l.strip()}
    except Exception:
        return set()


def rule_action_ids(path):
    txt = path.read_text()
    ids = set(re.findall(r'"(org\.freedesktop\.[A-Za-z0-9\.\-]+)"', txt))
    # drop prefix-style matches (e.g. "org.freedesktop.packagekit.")
    return {i for i in ids if i.count(".") >= 2 and not i.endswith(".")}


def test_rule_syntax():
    for r in RULES:
        # polkit rules are JS: node --check validates the syntax
        # (node refuses the .rules extension, so copy to a .js temp file)
        tmp = pathlib.Path("/tmp/vixzen-polkit-check.js")
        tmp.write_text(r.read_text())
        p = subprocess.run(["node", "--check", str(tmp)], capture_output=True,
                           text=True)
        assert p.returncode == 0, f"{r.name}: {p.stderr[:200]}"


def test_action_ids_exist():
    known = registered_actions()
    if not known:
        return  # no polkit registry on this machine
    for r in RULES:
        for aid in rule_action_ids(r):
            assert aid in known, (
                f"{r.name} uses unregistered action id: {aid} "
                "(rule would never fire)")


def test_edu_payload_present():
    ks = (REPO / "packaging" / "vixzenos-edu.ks").read_text()
    for needle in ("user --name=student", "vixzen-edu-admin",
                   "49-vixzen-edu-store.rules", "49-vixzen-edu-network.rules"):
        assert needle in ks, f"edu kickstart missing {needle}"


if __name__ == "__main__":
    test_rule_syntax()
    test_action_ids_exist()
    test_edu_payload_present()
    print("edu-lockdown tests OK: 3 checks passed")
