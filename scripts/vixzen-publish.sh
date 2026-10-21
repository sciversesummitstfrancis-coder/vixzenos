#!/bin/bash
# VixzenOS publish — build RPMs and push them to the VixzenOS COPR project.
# One-time setup (needs your accounts):
#   sudo dnf install -y copr-cli
#   copr-cli login                       # opens a browser, confirms your token
#   copr-cli create vixzen/vixzenos      # only the first time
# Then, for every release:
#   ./scripts/vixzen-publish.sh
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${VIXZEN_COPR_PROJECT:-vixzen/vixzenos}"
CHROOT="${VIXZEN_COPR_CHROOT:-fedora-44-x86_64}"

echo "== 1/3 building packages =="
"$HERE/scripts/vixzen-rpm-build.sh" || { echo "build failed"; exit 1; }

echo "== 2/3 checking COPR access =="
if ! command -v copr-cli >/dev/null; then
  echo "copr-cli missing — run: sudo dnf install -y copr-cli" >&2
  exit 1
fi
if ! copr-cli --help >/dev/null 2>&1; then
  echo "copr-cli is installed but not logged in — run: copr-cli login" >&2
  exit 1
fi
copr-cli list "$PROJECT" >/dev/null 2>&1 \
  && echo "project $PROJECT exists" \
  || { echo "creating project $PROJECT ..."; copr-cli create "$PROJECT"; }

echo "== 3/3 uploading =="
shopt -s nullglob
for rpm in "$HERE"/packaging/rpm/out/*.rpm; do
  echo "--> $(basename "$rpm")"
  copr-cli build-package "$PROJECT" "$rpm" 2>&1 | tail -n 3
done

echo
echo "Channel URL (add to client systems):"
echo "  https://copr.fedorainfracloud.org/groups/${PROJECT//\//\/}/$CHROOT/epr"
echo
echo "Client setup on a VixzenOS machine:"
echo "  sudo vixzen-repo-setup.sh"
