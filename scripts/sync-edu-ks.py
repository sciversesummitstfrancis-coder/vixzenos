#!/usr/bin/env python3
"""Regenerate the Edu kickstart from the Personal one, re-applying only the
Edu-specific deltas. Prevents the two editions from drifting apart (the
Edu copy fell behind when Personal gained the web browser, extensions, etc.).

Usage: python3 scripts/sync-edu-ks.py [--check]
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
PERSONAL = REPO / "packaging" / "vixzenos.ks"
EDU = REPO / "packaging" / "vixzenos-edu.ks"

EDU_HEADER = """# VixzenOS Edu kickstart — classroom edition (internet kill-switch + locked
# Software store for non-admins). Same desktop as Personal; adds a student
# account (no admin rights) + the Edu lockdown payload. Admin password is set
# at deploy time (passwd student / passwd <admin>); the live demo uses
# liveuser.
# Build: VXZ_KS=packaging/vixzenos-edu.ks sudo -E ./build-vixzenos.sh ./build/boot.iso
# (Needs the same build/boot.iso alongside)
"""

EDU_USER = """user --name=liveuser --groups=wheel --homedir=/home/liveuser
# Student: deliberately NOT in wheel, so the Edu polkit rules (network +
# PackageKit admin-only) apply. Password locked until the school sets it.
user --name=student --homedir=/home/student"""

EDU_PAYLOAD = """# --- Edu lockdown: admin helper (root-owned so students can't edit it),
# network control rule always-on, store rule shipped dormant until locked ---
install -m 755 /tmp/vixzen-stage/edu/vixzen-edu-admin.sh /usr/libexec/vixzen-edu-admin 2>/dev/null || true
mkdir -p /usr/share/vixzen-edu /usr/share/polkit-1/rules.d
cp /tmp/vixzen-stage/edu/49-vixzen-edu-store.rules /usr/share/vixzen-edu/ 2>/dev/null || true
cp /tmp/vixzen-stage/edu/49-vixzen-edu-network.rules /usr/share/polkit-1/rules.d/ 2>/dev/null || true
chmod 644 /usr/share/vixzen-edu/* /usr/share/polkit-1/rules.d/49-vixzen-edu-*.rules 2>/dev/null || true
echo "VIXZEN EDU payload installed" || true"""


def build_edu():
    txt = PERSONAL.read_text()
    # 1. header
    txt = re.sub(r"^# VixzenOS kickstart.*?#version=F44", EDU_HEADER + "#version=F44",
                 txt, count=1, flags=re.S)
    # 2. student user
    txt = txt.replace("user --name=liveuser --groups=wheel --homedir=/home/liveuser",
                      EDU_USER, 1)
    # 3. Edu payload, inserted right before the de-Fedora scrub block
    anchor = "# --- De-Fedora scrub:"
    assert anchor in txt, "de-Fedora anchor missing in personal kickstart"
    txt = txt.replace(anchor, EDU_PAYLOAD + "\n" + anchor, 1)
    return txt


def main():
    want = build_edu()
    cur = EDU.read_text()
    if "--check" in sys.argv:
        same = want == cur
        print("Edu kickstart in sync with Personal:", same)
        if not same:
            import difflib
            for line in list(difflib.unified_diff(
                    cur.splitlines(), want.splitlines(), "current", "expected",
                    lineterm=""))[:20]:
                print(line)
        return 0 if same else 1
    EDU.write_text(want)
    print("Edu kickstart regenerated from Personal + Edu deltas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
