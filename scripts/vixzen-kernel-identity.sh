#!/bin/bash
# VixzenOS kernel identity — make the kernel present as VixzenOS.
#
# This patches a kernel.spec so the upstream release tag never reaches the
# running system. It is idempotent: run it as often as you like.
#
#   ./scripts/vixzen-kernel-identity.sh [kernel.spec] [--check]
#
# Default spec: $HOME/rpmbuild/SPECS/kernel.spec
#
# What changes:
#   Release tag   200.fc44        -> 200.vixzen
#   uname -r      7.2.13-200.fc44.x86_64 -> 7.2.13-200.vixzen.x86_64
#   module dir    /lib/modules/7.2.13-200.fc44.x86_64 -> ...vixzen...
#   RPM NEVRA     kernel-7.2.13-200.fc44.x86_64 -> kernel-7.2.13-200.vixzen.x86_64
#
# It does NOT rewrite the kernel source, configs, patches or signing keys.
# Those stay upstream-compatible on purpose: the goal is a VixzenOS identity,
# not a forked kernel tree.
set -eu

SPEC="${1:-$HOME/rpmbuild/SPECS/kernel.spec}"
if [ "${SPEC}" = "--check" ]; then
  SPEC="$HOME/rpmbuild/SPECS/kernel.spec"
  CHECK_ONLY=1
else
  CHECK_ONLY=0
fi

[ -f "$SPEC" ] || { echo "vixzen-kernel-identity: no spec at $SPEC" >&2; exit 2; }

MARKER="VixzenOS kernel identity"

if [ "$CHECK_ONLY" -eq 0 ]; then
  # Back up the pristine spec once; later runs are idempotent edits on top.
  [ -f "$SPEC.before-vixzen-identity.bak" ] || cp -a "$SPEC" "$SPEC.before-vixzen-identity.bak"
  python3 - "$SPEC" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
marker = "VixzenOS kernel identity"
block = """# ---------------------------------------------------------------------------
# VixzenOS kernel identity
#
# The RPM dist tag is the one marker that leaks into every runtime surface:
#   uname -r              -> 7.2.13-200.vixzen.x86_64
#   /lib/modules/<ver>    -> ...vixzen...
#   RPM NEVRA             -> kernel-7.2.13-200.vixzen.x86_64
# Override it here so this kernel presents as VixzenOS while keeping the
# upstream configs, patches and build machinery intact.
# ---------------------------------------------------------------------------
%define dist .vixzen
%define dist_vendor VixzenOS
%define dist_name VixzenOS
%define dist_purl_namespace vixzenos
%define dist_home_url https://github.com/sciversesummitstfrancis-coder/vixzenos
%define dist_bug_report_url https://github.com/sciversesummitstfrancis-coder/vixzenos/issues

"""

if marker not in text:
    text = block + text

# The old Vixzen hack appended -vixzen to KernelVer only. That made the
# /lib/modules directory disagree with `uname -r`. The dist tag is the correct
# lever, so drop the suffix and let both names come from %{release}.
old = "KernelVer=%{specversion}-%{release}.%{_target_cpu}${Variant:++${Variant}}-vixzen"
new = "KernelVer=%{specversion}-%{release}.%{_target_cpu}${Variant:++${Variant}}"
text = text.replace(old, new)

# Secure Boot SBAT metadata should not advertise the upstream vendor either.
if "%global sbat_suffix vixzen" not in text:
    anchor = """%if 0%{?fedora}
%global sbat_suffix fedora
%else
%global sbat_suffix rhel
%endif
%endif
"""
    replacement = anchor + """
# VixzenOS: Secure Boot SBAT metadata is Vixzen-branded, not Fedora.
%global sbat_suffix vixzen
"""
    if anchor in text:
        text = text.replace(anchor, replacement, 1)

# Package-level branding: what `rpm -qi kernel` shows the user.
import re

if re.search(r"^Summary: The Linux kernel$", text, re.M):
    text = re.sub(r"^Summary: The Linux kernel$",
                  "Summary: VixzenOS Linux kernel", text, count=1, flags=re.M)

if not re.search(r"^Vendor:", text, re.M):
    tag = "%define dist_bug_report_url https://github.com/sciversesummitstfrancis-coder/vixzenos/issues\n"
    if tag in text:
        text = text.replace(tag, tag + "Vendor: VixzenOS\nPackager: VixzenOS\n", 1)

open(path, "w", encoding="utf-8").write(text)
PY
  echo "ensured VixzenOS kernel identity: $SPEC"
else
  echo "check-only: $SPEC"
fi

# Show the identity the spec now produces.
if command -v rpmspec >/dev/null; then
  echo "--- resulting kernel identity ---"
  rpmspec -q --qf '%{name}-%{version}-%{release}.%{arch}\n' "$SPEC" 2>/dev/null | head -n 1 || true
  echo "--- package branding ---"
  rpmspec -q --qf '%{summary}\n' "$SPEC" 2>/dev/null | head -n 1 | sed 's/^/summary: /' || true
  echo "--- expected uname -r ---"
  VER=$(rpmspec -q --qf '%{version}-%{release}.%{arch}\n' "$SPEC" 2>/dev/null | head -n 1 || true)
  [ -n "$VER" ] && echo "$VER" || echo "(rpmspec could not expand the spec)"
fi
