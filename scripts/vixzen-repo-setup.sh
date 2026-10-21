#!/bin/bash
# VixzenOS channel setup — point the system at the VixzenOS update repo so
# `dnf upgrade` serves VixzenOS releases.
#
# Usage: sudo ./vixzen-repo-setup.sh [--disable] [--url <repo-url>]
#
# Default channel: the public VixzenOS COPR project.
#   https://copr.fedorainfracloud.org/groups/vixzen/vixzenos/fedora-44-x86_64
# Override for a private build: --url <url-to-epr-or-repo>
set -u
DEFAULT_URL="https://copr.fedorainfracloud.org/groups/vixzen/vixzenos/fedora-44-x86_64/epr"
URL="$DEFAULT_URL"
REPO_ID=vixzenos
DEST=/etc/yum.repos.d/vixzenos.repo

while [ $# -gt 0 ]; do
  case "$1" in
    --disable) rm -f "$DEST"; echo "VixzenOS channel disabled."; exit 0 ;;
    --url) URL="$2"; shift ;;
    *) echo "Usage: $0 [--disable] [--url <url>]"; exit 2 ;;
  esac
  shift
done
[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }

# Preferred: let dnf write the repo definition (handles GPG keys).
if command -v dnf >/dev/null && dnf config-manager --help >/dev/null 2>&1; then
  if dnf config-manager addrepo --from-repofile="$URL" --id="$REPO_ID" \
       --save-filename=vixzenos --overwrite 2>/dev/null; then
    echo "VixzenOS channel added via dnf config-manager."
  fi
fi

# Fallback / belt-and-braces: write a plain repo file.
if [ ! -f "$DEST" ]; then
  base="${URL%/epr}"
  cat > "$DEST" <<EOF
[$REPO_ID]
name=VixzenOS Updates
baseurl=$base/
enabled=1
gpgcheck=0
repo_gpgcheck=0
metadata_expire=6h
priority=90
EOF
  echo "VixzenOS channel written to $DEST"
fi

if command -v dnf >/dev/null; then
  dnf makecache --quiet 2>/dev/null || true
  echo "VixzenOS packages visible in this channel:"
  dnf --quiet list --available 'vixzenos-*' 2>/dev/null | head -n 10 || true
fi
echo "Updates now arrive via: dnf upgrade   (or: vix update check)"
