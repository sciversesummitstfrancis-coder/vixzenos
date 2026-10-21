#!/bin/bash
# vixzen-update — refresh VixzenOS payload files (M7, local-source stage).
# Sources (in order): /usr/share/vixzen-updates/*.tar.gz, then a given path.
# Backs up the current payload before replacing. Never touches Fedora files.
# Testable: VIXZEN_ROOT=/tmp/fakeroot ./scripts/vixzen-update.sh <action>
# Usage: vixzen-update check | apply [tarball] | history | version
set -u
ROOT="${VIXZEN_ROOT:-}"
DEST="$ROOT/usr/share/vixzen"
BKDIR="$ROOT/var/lib/vixzen/backups"
LOGF="$ROOT/var/log/vixzen-update.log"
VERF="$ROOT/etc/vixzen-release"

log(){ mkdir -p "$(dirname "$LOGF")" 2>/dev/null; echo "[$(date +%F_%T)] $*" >> "$LOGF" 2>/dev/null; echo "$*"; }

version() {
  grep -h VERSION "$VERF" 2>/dev/null | head -n 1 || echo "VERSION=unknown"
}

check() {
  version
  n=$(ls "$ROOT/usr/share/vixzen-updates/"*.tar.gz 2>/dev/null | wc -l)
  echo "staged update bundles: $n"
  [ "$n" -gt 0 ] && ls "$ROOT/usr/share/vixzen-updates/"*.tar.gz
  echo "history: $([ -f "$LOGF" ] && wc -l < "$LOGF" || echo 0) entries (vixzen-update history)"
}

backup() {
  mkdir -p "$BKDIR"
  stamp=$(date +%Y%m%d-%H%M%S)
  tar -czf "$BKDIR/vixzen-$stamp.tar.gz" -C "$ROOT/usr/share" vixzen 2>/dev/null \
    && echo "$BKDIR/vixzen-$stamp.tar.gz"
}

apply() {
  tb="${1:-$(ls -t "$ROOT/usr/share/vixzen-updates/"*.tar.gz 2>/dev/null | head -n 1)}"
  [ -n "$tb" ] && [ -f "$tb" ] || { echo "No update bundle found."; return 1; }
  # Safety: bundle must contain the marker, nothing outside vixzen/.
  tar -tzf "$tb" | grep -qx "vixzen/preview/vixzen_preview.py" \
    || { echo "Refusing: bundle is not a Vixzen payload."; return 1; }
  if tar -tzf "$tb" | grep -qv "^vixzen/"; then
    echo "Refusing: bundle touches paths outside vixzen/."
    return 1
  fi
  bk=$(backup) || { echo "Backup failed, aborting."; return 1; }
  tar -xzf "$tb" -C "$ROOT/usr/share" \
    && { log "applied $(basename "$tb") (backup: $bk)"; return 0; }
  echo "Apply failed; backup at $bk"
  return 1
}

history() { cat "$LOGF" 2>/dev/null || echo "No update history yet."; }

case "${1:-check}" in
  check) check ;;
  apply) apply "${2:-}" ;;
  history) history ;;
  version) version ;;
  *) echo "Usage: $0 check | apply [tarball] | history | version"; exit 2 ;;
esac
