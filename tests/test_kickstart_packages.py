"""Kickstart package availability check.

A package that cannot be downloaded from the repos the live-build
installer knows about aborts the whole 2-hour ISO build (chromium lives
only in RPM Fusion -> "No more mirrors to try" -> build dies).

This test resolves every %packages entry against the FEDORA repos only
(RPM Fusion / COPR excluded) so a bad entry fails the fast test suite
instead of the slow build.
"""
import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[1]
KS = [REPO / "packaging" / "vixzenos.ks",
      REPO / "packaging" / "vixzenos-edu.ks"]


def ks_packages(ks):
    txt = ks.read_text()
    block = txt[txt.index("%packages"):txt.index("%end")]
    return [p for p in re.findall(r"^([a-zA-Z0-9\-\_\.\+@]+)$", block, re.M)
            if not p.startswith("@")]


def in_fedora(pkg):
    r = subprocess.run(
        ["dnf", "--disablerepo=*fusion*", "--disablerepo=*copr*",
         "repoquery", pkg],
        capture_output=True, text=True, timeout=180)
    return bool(r.stdout.strip())


def test_groups_exist():
    # dnf lists environment/product groups by their id without the "@";
    # anaconda accepts "@id". Match on the id substring.
    out = subprocess.run(["dnf", "group", "list", "--hidden"],
                         capture_output=True, text=True, timeout=240).stdout
    for ks in KS:
        txt = ks.read_text()
        block = txt[txt.index("%packages"):txt.index("%end")]
        for grp in re.findall(r"^(@[a-zA-Z0-9\-\_\.\+]+)$", block, re.M):
            gid = grp.lstrip("@")
            # dnf5 and anaconda name this group differently
            # (@workstation-product-environment vs workstation-product).
            ok = (gid in out) or (gid.replace("-environment", "") in out)
            assert ok, f"{ks.name}: group {grp} not found"


def test_packages_available():
    missing = []
    for ks in KS:
        for pkg in ks_packages(ks):
            if not in_fedora(pkg):
                missing.append((ks.name, pkg))
    assert not missing, (
        f"not available in Fedora proper (would abort the ISO build): {missing}")


if __name__ == "__main__":
    test_groups_exist()
    test_packages_available()
    print("kickstart-package tests OK: 2 checks passed")
