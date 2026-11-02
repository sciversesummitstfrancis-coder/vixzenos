"""VixzenOS identity tests — the de-Fedora boundary must not regress.

These are static checks. They do not build an ISO; they assert that the
identity files, kickstarts, kernel patcher and shipped CSS keep saying
VixzenOS and never leak the upstream release tag into user-visible surfaces.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[1]
KS_ALL = [REPO / "packaging" / "vixzenos.ks",
          REPO / "packaging" / "vixzenos-edu.ks"]
RELEASE = REPO / "packaging" / "rpm" / "vixzen-release"
KERNEL_ID = REPO / "scripts" / "vixzen-kernel-identity.sh"

# Upstream brand markers that must never reach a running VixzenOS system.
FORBIDDEN_IDENTITY = ("ID_LIKE", "CPE_NAME", "Fedora-based", "fedora-release")


def test_release_file_is_fully_vixzen():
    text = RELEASE.read_text()
    fields = dict(re.findall(r"^([A-Z_]+)=[\"']?(.*?)[\"']?$", text, re.M))
    assert fields["ID"] == "vixzenos"
    assert fields["NAME"] == "VixzenOS"
    assert fields["VARIANT_ID"] == "vixzenos"
    assert "ANSI_COLOR" in fields and fields["ANSI_COLOR"].endswith("59;130;246")
    for marker in FORBIDDEN_IDENTITY:
        assert marker not in text, f"{marker} in {RELEASE}"


def test_kickstarts_rewrite_os_release():
    for ks in KS_ALL:
        text = ks.read_text()
        block = re.search(r"cat > /etc/vixzen-release.*?^EOF$", text, re.M | re.S)
        assert block, f"no /etc/vixzen-release block in {ks}"
        body = block.group(0)
        assert 'ID=vixzenos' in body
        assert "ID_LIKE" not in body
        assert "CPE_NAME" not in body
        assert "Fedora-based" not in body
        # os-release must be replaced, not patched field-by-field.
        assert "cp /etc/vixzen-release /usr/lib/os-release" in text, ks
        assert "rm -f /etc/os-release" in text, ks
        # DNF still needs a release number, pinned outside os-release.
        assert "echo \"44\" > /etc/dnf/vars/releasever" in text, ks


def test_no_user_visible_fedora_release_read():
    offenders = []
    for path in (REPO / "apps").rglob("*.py"):
        text = path.read_text(errors="ignore")
        if "/etc/fedora-release" in text:
            offenders.append(str(path.relative_to(REPO)))
    assert not offenders, f"apps still read fedora-release: {offenders}"


def test_browser_bookmarks_point_at_vixzen_docs():
    text = (REPO / "apps" / "web-browser" / "web_core.py").read_text()
    assert "docs.fedoraproject.org" not in text


def test_no_legacy_indigo_accent_in_shipped_css():
    legacy = ("#7C7CFF", "#4F46E5", "#3730A3", "#7c7cff", "#4f46e5")
    bad = []
    files = (list(REPO.glob("assets/**/*.css"))
             + list(REPO.glob("apps/**/*.py"))
             + list(REPO.glob("website/**/*.css")))
    for path in files:
        text = path.read_text(errors="ignore")
        for marker in legacy:
            if marker in text and path.name != "make_vixzen_neon.py":
                bad.append(f"{path.relative_to(REPO)}: {marker}")
    assert not bad, "legacy indigo accents remain:\n" + "\n".join(bad)


def test_website_screenshots_have_no_legacy_accent():
    """The committed screenshots must be from the blue era, not the old neon."""
    try:
        from PIL import Image
    except ImportError:
        return  # Pillow is optional on a bare test host.
    import colorsys
    shots = sorted((REPO / "website" / "assets").glob("shot-*.png"))
    assert shots, "website screenshots are missing"
    bad = []
    for path in shots:
        im = Image.open(path).convert("RGB")
        im.thumbnail((320, 180))
        data = im.tobytes()
        hits = 0
        for i in range(0, len(data), 3):
            r, g, b = data[i], data[i + 1], data[i + 2]
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s < 0.35 or v < 0.28:
                continue
            deg = h * 360
            if (228 <= deg <= 268 and abs(r - g) <= 26 and b >= g + 40) or \
               (122 <= deg <= 172 and g >= r + 40 and g >= b + 20):
                hits += 1
        if hits:
            bad.append(f"{path.name}: {hits} legacy-accent px")
    assert not bad, ("screenshots still show old accents; run "
                     "scripts/vixzen-recolor-shots.py:\n" + "\n".join(bad))


def test_kernel_identity_patcher_defines_vixzen_dist():
    text = KERNEL_ID.read_text()
    assert "%define dist .vixzen" in text, "patcher must override the RPM dist tag"
    assert "%global sbat_suffix vixzen" in text
    # The legacy -vixzen KernelVer suffix is what made /lib/modules disagree
    # with uname -r; the patcher must remove it and let %{release} carry the tag.
    old_line = re.search(r'^old = "KernelVer=.*"$', text, re.M)
    new_line = re.search(r'^new = "KernelVer=.*"$', text, re.M)
    assert old_line and new_line, "patcher must rewrite the KernelVer line"
    assert "-vixzen" in old_line.group(0)
    assert "-vixzen" not in new_line.group(0)
    assert "${Variant:++${Variant}}" in new_line.group(0)


def test_public_copy_does_not_claim_fedora_base():
    public = [REPO / "README.md", REPO / "website" / "index.html"]
    for path in public:
        text = path.read_text().lower()
        assert "fedora base" not in text, path
        assert "built on fedora" not in text, path
        assert "fedora-based" not in text, path


def test_every_package_spec_uses_vixzen_dist_tag():
    import shutil
    import subprocess
    if not shutil.which("rpmspec"):
        return
    for spec in sorted((REPO / "packaging" / "rpm" / "SPECS").glob("*.spec")):
        assert "%define dist .vixzen" in spec.read_text(), spec
        out = subprocess.run(
            ["rpmspec", "-q", "--qf",
             "%{name}-%{version}-%{release}.%{arch}\n", str(spec)],
            capture_output=True, text=True, timeout=30, check=True).stdout
        first = out.splitlines()[0]
        assert first.endswith(".vixzen.noarch"), (spec.name, first)
        assert ".fc" not in first, (spec.name, first)
