#!/bin/bash
# VixzenOS release builder — packages the tree as RPMs, makes a local repo,
# and (with copr-cli configured) publishes to the VixzenOS COPR project.
# Usage: ./scripts/vixzen-rpm-build.sh [--repo-only] [--publish]
#
# NOTE: rpmbuild cannot handle spaces in its paths, so the build always
# happens under /tmp/vixzen-rpm-* (symlinked to the repo) and only the
# finished RPMs are copied back into the repository.
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
RPMDIR="$HERE/packaging/rpm"
SRCLINK=/tmp/vixzen-rpm-src
BUILDDIR=/tmp/vixzen-rpm-build
OUT="$RPMDIR/out"
VERSION="$(cat "$RPMDIR/VERSION" 2>/dev/null || echo 0.3)"

log(){ echo "[rpm-build] $*"; }

# 1. Stage the tree as the source payload (no spaces in the path).
rm -rf "$SRCLINK" "$BUILDDIR"
mkdir -p "$BUILDDIR"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
ln -sfn "$HERE" "$SRCLINK"
mkdir -p "$BUILDDIR/SOURCES/vixzen-tree"
for d in apps assets desktop packaging preview scripts shared website; do
  [ -d "$SRCLINK/$d" ] && cp -a "$SRCLINK/$d" "$BUILDDIR/SOURCES/vixzen-tree/" 2>/dev/null || true
done
# Keep the payload lean: no caches, no duplicated vendored frames.
rm -rf "$BUILDDIR/SOURCES/vixzen-tree"/*/__pycache__ 2>/dev/null || true
rm -f "$BUILDDIR/SOURCES/vixzen-tree"/assets/boot/frames/*.png 2>/dev/null || true
log "source tree staged ($(du -sh "$BUILDDIR/SOURCES/vixzen-tree" | cut -f1))"

# 2. Build every spec.
cp "$RPMDIR"/SPECS/*.spec "$BUILDDIR/SPECS/"
for spec in "$BUILDDIR"/SPECS/*.spec; do
  name=$(basename "$spec" .spec)
  rpmbuild --define "_topdir $BUILDDIR" --define "_sourcedir $BUILDDIR/SOURCES" \
    -bb "$spec" >"$BUILDDIR/$name.log" 2>&1 \
    && log "built $name" \
    || { log "FAILED $name (see $BUILDDIR/$name.log)"; grep -E "^(error|.*: error)" "$BUILDDIR/$name.log" | head -n 6; }
done

# 3. Collect + local repo.
rm -rf "$OUT"; mkdir -p "$OUT"
find "$BUILDDIR/RPMS" -name "*.rpm" -exec cp {} "$OUT"/ \; 2>/dev/null
if compgen -G "$OUT/*.rpm" >/dev/null; then
  createrepo_c --quiet "$OUT" 2>/dev/null || true
  log "local repo metadata in $OUT/repodata"
  log "packages:"
  ls -1 "$OUT"/*.rpm | sed 's|.*/|  |'
else
  log "no packages built"
  exit 1
fi

# 4. Optional publish to the VixzenOS COPR project.
if [ "${1:-}" = "--publish" ]; then
  if ! command -v copr-cli >/dev/null; then
    log "copr-cli missing: sudo dnf install copr-cli && copr-cli login"
    exit 1
  fi
  for rpm in "$OUT"/*.rpm; do
    copr-cli build-package vixzen/vixzenos "$rpm" 2>&1 | tail -n 3
  done
  log "uploaded to copr: vixzen/vixzenos"
fi
