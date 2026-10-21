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
# copr-cli 2.7 has no `login` subcommand: authentication is done by
# storing login+token in ~/.config/copr (copr_url + [copr-cli] section).
# Get a token from https://copr.fedorainfracloud.org/api/ after signing in.
CFG="$HOME/.config/copr"
if [ ! -f "$CFG" ] || ! grep -qE "^token\s*=\s*\S+" "$CFG" 2>/dev/null; then
  echo "not logged in to COPR. Do this once:" >&2
  echo "  1. sign in at https://copr.fedorainfracloud.org" >&2
  echo "  2. open  https://copr.fedorainfracloud.org/api/  -> request an API token" >&2
  echo "  3. write them into ~/.config/copr:" >&2
  echo "       [copr-cli]" >&2
  echo "       copr_url = https://copr.fedorainfracloud.org" >&2
  echo "       login = <your-copr-login>" >&2
  echo "       token = <your-token>" >&2
  exit 1
fi
echo "logged in as: $(copr-cli whoami 2>/dev/null | head -n 1)"

PROJECT_CREATED=0
if ! copr-cli get "$PROJECT" >/dev/null 2>&1; then
  echo "creating project $PROJECT ..."
  copr-cli create "$PROJECT" || exit 1
  PROJECT_CREATED=1
fi
# Pick a chroot that exists in the project.
CHROOT_USED=""
for c in "$CHROOT" fedora-44-x86_64 fedora-rawhide-x86_64; do
  if copr-cli get-chroot "$PROJECT" "$c" >/dev/null 2>&1; then
    CHROOT_USED="$c"; break
  fi
done
[ -n "$CHROOT_USED" ] || { echo "no usable chroot in $PROJECT"; exit 1; }
echo "target chroot: $CHROOT_USED"

echo "== 3/3 uploading =="
shopt -s nullglob
for rpm in "$HERE"/packaging/rpm/out/*.rpm; do
  base=$(basename "$rpm")
  pkgname=$(rpm -qp --qf "%{NAME}" "$rpm" 2>/dev/null)
  echo "--> $base ($pkgname)"
  copr-cli build-package "$PROJECT" "$rpm" --name "$pkgname" \
    -r "$CHROOT_USED" --nowait 2>&1 | tail -n 2
done

echo
echo "Channel URL (add to client systems):"
echo "  https://copr.fedorainfracloud.org/groups/${PROJECT}/$CHROOT_USED/epr"
echo
echo "Client setup on a VixzenOS machine:"
echo "  sudo vixzen-repo-setup.sh"
