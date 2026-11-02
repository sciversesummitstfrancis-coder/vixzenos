#!/bin/bash
# VixzenOS kernel identity — make the kernel present as VixzenOS, not Fedora.
#
# This patches a kernel.spec so the Fedora dist tag ("fc44") never reaches the
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

if [ "$CHECK_ONLY" -eq 0 ] && ! grep -q "$MARKER" "$SPEC"; then
  cp -a "$SPEC" "$SPEC.before-vixzen-identity.bak"
  python3 - "$SPEC" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()
marker = "VixzenOS kernel identity"
block = """# ---------------------------------------------------------------------------
# VixzenOS kernel identity
#
# The dist tag is the only Fedora marker that leaks into the running system:
#   uname -r              -> 7.2.13-200.fc44.x86_64
#   /lib/modules/<ver>    -> ...fc44...
#   RPM NEVRA             -> kernel-7.2.13-200.fc44.x86_64
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

# Secure Boot SBAT metadata should not advertise Fedora either.
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

open(path, "w", encoding="utf-8").write(text)
PY
  echo "patched: $SPEC"
else
  echo "already patched or check-only: $SPEC"
fi

# Show the identity the spec now produces.
if command -v rpmspec >/dev/null; then
  echo "--- resulting kernel identity ---"
  rpmspec -q --qf '%{name}-%{version}-%{release}.%{arch}\n' "$SPEC" 2>/dev/null | head -n 1 || true
  echo "--- expected uname -r ---"
  VER=$(rpmspec -q --qf '%{version}-%{release}.%{arch}\n' "$SPEC" 2>/dev/null | head -n 1 || true)
  [ -n "$VER" ] && echo "$VER" || echo "(rpmspec could not expand the spec)"
fi
