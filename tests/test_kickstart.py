"""Structural tests for kickstarts + build script (headless, no sudo).

Catches the failure classes from real builds: missing stage payloads,
dead GRUB defaults, EFI blindness, dconf breakage, edition drift.
"""
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
KS = REPO / "packaging" / "vixzenos.ks"
EDU = REPO / "packaging" / "vixzenos-edu.ks"
BUILD = REPO / "build-vixzenos.sh"

REQUIRED_PKGS = ["grub2-efi-x64-cdboot", "shim-x64", "curl", "unzip",
                 "dracut-live", "livesys-scripts", "plymouth",
                 "cool-retro-term", "fastfetch", "cava", "cmatrix"]


def _posts(path):
    return re.findall(r"%post(.*?)%end", pathlib.Path(path).read_text(),
                      re.S)


def test_no_efi_partition():
    for ks in (KS, EDU):
        assert "part /boot/efi" not in ks.read_text(), ks


def test_required_packages():
    for ks in (KS, EDU):
        txt = ks.read_text()
        for pkg in REQUIRED_PKGS:
            assert re.search(rf"^{re.escape(pkg)}$", txt, re.M), (ks, pkg)


def test_stage_refs_resolve():
    import os
    tmp = os.environ.get("VIXZEN_STAGE_CHECK", "/tmp/vixzen-stage")
    refs = sorted(set(re.findall(r"/tmp/vixzen-stage/[A-Za-z0-9_.\-/*]+",
                                 KS.read_text())))
    assert refs, "no stage refs found (regex broke?)"
    if tmp and os.path.isdir(tmp):
        for r in refs:
            base = r.replace("/tmp/vixzen-stage", tmp).split("*")[0].rstrip("/")
            assert os.path.exists(base), r


def test_dconf_parses():
    for ks in (KS, EDU):
        m = re.search(r"cat > /etc/dconf/db/local.d/00-vixzen <<'EOF'(.*?)EOF",
                      ks.read_text(), re.S)
        assert m, ks
        cur, seen = None, set()
        for i, raw in enumerate(m.group(1).splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if re.match(r"\[.+\]", line):
                cur = line
                continue
            assert "=" in line and cur is not None, (ks, i, raw)
            key = (cur, line.split("=")[0])
            assert key not in seen, f"duplicate key {key} in {ks}"
            seen.add(key)
        groups = {g for g, _ in seen}
        assert "[org/gnome/shell]" in groups
        assert "[org/gnome/desktop/background]" in groups


def test_grub_direct_boot_templates():
    lt = (REPO / "packaging" / "lorax-templates-99-generic" / "live"
          / "config_files" / "x86")
    for f in ("grub2-bios.cfg", "grub2-efi.cfg"):
        assert 'set default="0"' in (lt / f).read_text(), f


def test_post_bash_syntax():
    for ks in (KS, EDU):
        for i, p in enumerate(_posts(ks)):
            f = pathlib.Path(f"/tmp/vixzen-ks-test-{ks.stem}-{i}.sh")
            f.write_text("\n".join(p.split("\n")[1:]))
            r = subprocess.run(["bash", "-n", str(f)],
                               capture_output=True, text=True)
            assert r.returncode == 0, (ks, i, r.stderr)


def test_edition_parity():
    base, edu = KS.read_text(), EDU.read_text()
    for marker in ("usr/local/bin/vix", "LIVE-OFF", "xconfig --startxonboot",
                   "AutomaticLogin=liveuser"):
        assert marker in base, marker
        assert marker in edu, ("edu missing", marker)
    assert "user --name=student" in edu


def test_build_script_guards():
    txt = BUILD.read_text()
    assert "implantiso88515".replace("88515", "md5") in txt
    assert "--lorax-templates" in txt
    assert "--project VixzenOS" in txt
    assert "vix\" doctor" in txt or "command-center/vix" in txt


def test_version_consistency():
    ver = (REPO / "packaging" / "VERSION").read_text().strip()
    assert re.match(r"^\d+\.\d+$", ver), ver
    ks = KS.read_text()
    assert f'VERSION="{ver} (Preview)"' in ks
    html = (REPO / "website" / "index.html").read_text()
    assert ver in html
    meta = (REPO / "desktop" / "shell" / "metadata.json").read_text()
    assert '"shell-version": ["50"]' in meta  # shell target pinned with release


if __name__ == "__main__":
    test_no_efi_partition()
    test_required_packages()
    test_stage_refs_resolve()
    test_dconf_parses()
    test_grub_direct_boot_templates()
    test_post_bash_syntax()
    test_edition_parity()
    test_build_script_guards()
    test_version_consistency()
    print("kickstart tests OK: 9 checks passed")
