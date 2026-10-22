#!/bin/bash
# VixzenOS ISO builder — safe by default. Never touches disks/bootloader.
# Usage: ./build-vixzenos.sh [--check-only] [--clean]
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
LOG="$HERE/build/build.log"
# Variant select: VXZ_KS=packaging/vixzenos-edu.ks sudo -E ./build-vixzenos.sh
KS="$HERE/${VXZ_KS:-packaging/vixzenos.ks}"
mkdir -p "$HERE/build"

log(){ echo "$*" | tee -a "$LOG"; }
: > "$LOG"

MODE="${1:-full}"   # no args = full build; --check-only / --clean for the safe modes
# Optional boot-ISO path as first arg: sudo ./build-vixzenos.sh /path/to/boot.iso
if [ "${MODE#-}" != "$MODE" ]; then :; else
  [ -f "$MODE" ] && { BOOT_ISO_ARG="$MODE"; MODE=full; }
fi
log "=== VixzenOS build ($MODE) ==="

fail=0
for cmd in python3 livemedia-creator lorax; do
  command -v "$cmd" >/dev/null && log "[OK] $cmd: $(command -v $cmd)" \
    || { log "[MISSING] $cmd"; fail=1; }
done
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1')" \
  >>"$LOG" 2>&1 && log "[OK] GTK4+Libadwaita Python bindings" \
  || { log "[MISSING] python3-gobject/gtk4"; fail=1; }
[ -f "$KS" ] && log "[OK] kickstart $KS" || { log "[MISSING] $KS"; fail=1; }
LT="$HERE/packaging/lorax-templates-99-generic/live/config_files/x86"
if grep -q 'set default="0"' "$LT/grub2-bios.cfg" "$LT/grub2-efi.cfg" 2>/dev/null; then
  log "[OK] lorax templates (GRUB default=direct boot)"
else
  log "[MISSING] vendored lorax templates"; fail=1
fi
[ -f "$HERE/preview/src/vixzen_preview.py" ] && log "[OK] preview app" \
  || { log "[MISSING] preview app"; fail=1; }

avail_kb=$(df --output=avail "$HERE" | tail -1)
log "[INFO] free space: $((avail_kb/1024/1024)) GB"
[ "$avail_kb" -lt 20971520 ] && log "[WARN] < 20 GB free — full ISO may fail; --check-only still fine."

log "[TEST] preview smoke…"
python3 "$HERE/preview/src/vixzen_preview.py" --smoke 2>&1 | tee -a "$LOG" \
  || { log "[FAIL] preview smoke test"; fail=1; }
python3 "$HERE/apps/file-manager/vixzen_files.py" --smoke 2>&1 | tee -a "$LOG" \
  || { log "[FAIL] files smoke test"; fail=1; }
python3 "$HERE/apps/system-settings/vixzen_settings.py" --smoke 2>&1 | tee -a "$LOG" \
  || { log "[FAIL] settings smoke test"; fail=1; }
python3 "$HERE/apps/power-menu/vixzen_power.py" --smoke 2>&1 | tee -a "$LOG" \
  || { log "[FAIL] startmenu smoke test"; fail=1; }
python3 "$HERE/apps/web-browser/vixzen_web.py" --smoke 2>&1 | tee -a "$LOG" \
  || { log "[FAIL] web smoke test"; fail=1; }
if python3 -c "from PyQt6 import QtWebEngineWidgets" 2>/dev/null \
   || python3 -c "from PySide6 import QtWebEngineWidgets" 2>/dev/null; then
  python3 "$HERE/apps/web-browser-blink/vixzen_blink.py" --smoke 2>&1 | tee -a "$LOG" \
    || { log "[FAIL] blink smoke test"; fail=1; }
else
  log "[SKIP] blink smoke (no Qt WebEngine bindings; web build unaffected)"
fi
"$HERE/apps/command-center/vix" doctor --json >/dev/null 2>&1; rc=$?
[ "$rc" -le 2 ] || { log "[FAIL] vix smoke test (rc=$rc)"; fail=1; }

log "[STAGE] assembling /tmp/vixzen-stage (what the ISO %post installs)…"
STAGE=/tmp/vixzen-stage
rm -rf "$STAGE" 2>/dev/null || {
  log "[HINT] $STAGE is root-owned (from an earlier sudo run)."
  log "[HINT] Run once: sudo rm -rf $STAGE — then rerun this script."
  fail=1
}
mkdir -p "$STAGE"/{preview,files,settings,power,web,boot,wallpapers,shell}
cp "$HERE"/preview/src/*.py "$STAGE/preview/" 2>/dev/null || fail=1
cp "$HERE"/apps/file-manager/*.py "$STAGE/files/" 2>/dev/null || fail=1
cp "$HERE"/apps/system-settings/*.py "$STAGE/settings/" 2>/dev/null || fail=1
cp "$HERE"/apps/power-menu/*.py "$STAGE/power/" 2>/dev/null || fail=1
cp "$HERE"/apps/web-browser/*.py "$STAGE/web/" 2>/dev/null || fail=1
mkdir -p "$STAGE/blink"
cp "$HERE"/apps/web-browser-blink/*.py "$STAGE/blink/" 2>/dev/null || true
cp "$HERE"/apps/web-browser-blink/vixzen-blink "$HERE"/apps/web-browser-blink/*.desktop "$STAGE/blink/" 2>/dev/null || true
cp "$HERE"/apps/web-browser/vixzen-web "$STAGE/web/" 2>/dev/null || true
cp "$HERE"/apps/web-browser/*.desktop "$STAGE/web/" 2>/dev/null || true
cp "$HERE"/assets/branding/vixzen-web.svg "$STAGE/" 2>/dev/null || true
cp "$HERE"/desktop/shell/extension.js "$HERE"/desktop/shell/metadata.json "$STAGE/shell/" 2>/dev/null || fail=1
cp "$HERE"/desktop/shell/vendor/*.zip "$STAGE/shell/" 2>/dev/null || log "[WARN] no vendored shell extensions"
mkdir -p "$STAGE/widgets"
cp "$HERE"/desktop/widgets/* "$STAGE/widgets/" 2>/dev/null || log "[WARN] no vixzen widgets"
cp "$HERE"/assets/boot/*.png "$STAGE/boot/" 2>/dev/null || fail=1
mkdir -p "$STAGE/boot/frames"
cp "$HERE"/assets/boot/frames/*.png "$STAGE/boot/frames/" 2>/dev/null \
  || log "[WARN] no boot frames (spinner fallback at boot)"
cp "$HERE"/assets/wallpapers/*.png "$STAGE/wallpapers/" 2>/dev/null || true
cp "$HERE"/assets/icons/vixzen-search.svg "$HERE"/assets/branding/logo.svg "$STAGE/" 2>/dev/null || true
mkdir -p "$STAGE"/icons "$STAGE"/gtheme "$STAGE"/gtk
cp -a "$HERE"/assets/icons/theme/Vixzen "$STAGE/icons/" 2>/dev/null || fail=1
cp "$HERE"/assets/shell-theme/gnome-shell.css "$STAGE/gtheme/" 2>/dev/null || fail=1
cp "$HERE"/assets/gtk-theme/*.css "$STAGE/gtk/" 2>/dev/null || fail=1
mkdir -p "$STAGE/edu"
cp "$HERE"/scripts/vixzen-edu-admin.sh "$STAGE/edu/" 2>/dev/null || log "[WARN] no edu helper"
cp "$HERE"/packaging/edu-polkit/*.rules "$STAGE/edu/" 2>/dev/null || log "[WARN] no edu polkit rules"
mkdir -p "$STAGE/cmd"
cp "$HERE"/apps/command-center/vix "$STAGE/cmd/" 2>/dev/null || fail=1
cp -a "$HERE"/apps/command-center/vixcmd "$STAGE/cmd/" 2>/dev/null || fail=1
mkdir -p "$STAGE/core"
cp "$HERE"/shared/vixzen_core/*.py "$STAGE/core/" 2>/dev/null || fail=1
mkdir -p "$STAGE/update"
cp "$HERE"/scripts/vixzen-update.sh "$STAGE/update/" 2>/dev/null || fail=1
cp "$HERE"/scripts/de-fedora.sh "$STAGE/" 2>/dev/null || fail=1
mkdir -p "$STAGE/cursors"
cp -a "$HERE"/assets/cursors/WhiteSur "$STAGE/cursors/" 2>/dev/null || fail=1
mkdir -p "$STAGE/looks"
# The full "looks" bundle: WhiteSur GTK theme + WhiteSur/Tela icon sets +
# macOS wallpapers, so a fresh VixzenOS boots looking like the host.
cp -a "$HERE"/assets/gtk-theme/WhiteSur-Dark-blue "$STAGE/looks/" 2>/dev/null || true
cp -a "$HERE"/assets/icons/theme/WhiteSur-dark "$STAGE/looks/" 2>/dev/null || true
cp -a "$HERE"/assets/wallpapers/whitesur "$STAGE/looks/" 2>/dev/null || true
cp "$HERE"/assets/branding/* "$STAGE/" 2>/dev/null || true
cp "$HERE"/assets/wallpapers/* "$STAGE/" 2>/dev/null || true
find "$STAGE" -type f | tee -a "$LOG" >/dev/null
log "[STAGE] $(find "$STAGE" -type f | wc -l) files staged."
rm -f /tmp/vixzen-stage.tar.gz
tar -czf /tmp/vixzen-stage.tar.gz -C /tmp vixzen-stage 2>>"$LOG" \
  && log "[STAGE] tarball /tmp/vixzen-stage.tar.gz ($(du -h /tmp/vixzen-stage.tar.gz | cut -f1))" \
  || { log "[FAIL] stage tarball (see $LOG)"; fail=1; }
# Sudo runs create root-owned files; hand the stage back so the next
# user-owned run doesn't trip over permissions.
[ -n "${SUDO_USER:-}" ] && chown -R "$SUDO_USER" "$STAGE" 2>/dev/null || true
if command -v desktop-file-validate >/dev/null; then
  log "[VALIDATE] .desktop syntax…"
  python3 -c "
import pathlib
ks = pathlib.Path('$HERE/packaging/vixzenos.ks').read_text()
assert 'os.vixzen.preview.desktop' in ks and 'os.vixzen.files.desktop' in ks, 'desktop entries missing from ks'
print('ks desktop entries OK')
" 2>&1 | tee -a "$LOG" || { log "[FAIL] ks desktop check"; fail=1; }
else
  log "[SKIP] desktop-file-validate not installed (optional)."
fi
if command -v ksvalidator >/dev/null; then
  ksvalidator "$KS" 2>&1 | tee -a "$LOG" || { log "[FAIL] ksvalidator"; fail=1; }
else
  log "[SKIP] ksvalidator not installed (optional; kickstart still staged)."
fi

if [ "$MODE" = "--clean" ]; then
  rm -rf "$HERE/build" "$HERE"/preview/src/__pycache__ && mkdir -p "$HERE/build"
  log "[OK] cleaned."; exit 0
fi
if [ "$MODE" = "--check-only" ]; then
  [ "$fail" -eq 0 ] && log "[OK] check-only passed. Run without flags (needs sudo) for real ISO." \
    || log "[FAIL] fix the MISSING items above."
  exit "$fail"
fi

# Full build — explicit, privileged, documented.
if [ "$(id -u)" -ne 0 ]; then
  log "[STOP] Full ISO needs sudo: sudo ./build-vixzenos.sh"
  log "       (livemedia-creator mounts filesystems). Nothing was changed."
  exit 2
fi
# livemedia demands a NON-EXISTENT result dir and a boot ISO to install from.
RESULTDIR="$HERE/build/iso-result"
BOOT_ISO="${BOOT_ISO_ARG:-${2:-${BOOT_ISO:-$HERE/build/boot.iso}}}"
if [ ! -f "$BOOT_ISO" ]; then
  log "[STOP] Boot ISO missing: $BOOT_ISO"
  log "       Download 'Fedora Everything netinst' for Fedora 44 from:"
  log "       https://getfedora.org (Everything -> network installer, x86_64)"
  log "       Save it as: $HERE/build/boot.iso — then rerun sudo ./build-vixzenos.sh"
  exit 3
fi
rm -rf "$RESULTDIR"
log "[BUILD] serving /tmp/vixzen-stage.tar.gz on 10.0.2.2:8008 for VM %post fetch…"
# VM install cannot see host /tmp; serve the tarball over user-net HTTP.
# Guest reaches host at 10.0.2.2. Kill server on exit.
python3 -m http.server 8008 --directory /tmp >/dev/null 2>&1 &
HTTP_PID=$!
trap 'kill $HTTP_PID 2>/dev/null || true' EXIT
sleep 1
curl -s -o /dev/null http://127.0.0.1:8008/vixzen-stage.tar.gz \
  && log "[OK] stage HTTP up" || log "[WARN] stage HTTP not reachable (branding may be missing, ISO still bootable)"
log "[BUILD] livemedia-creator --make-iso --iso $BOOT_ISO --ks $KS --resultdir $RESULTDIR …"
# Vendored lorax templates: identical to system 99-generic except GRUB
# default="0" (boot straight in; the media-check entry stays available).
# Branding flags turn "Linux 44" into "VixzenOS" in GRUB + ISO label
# (project and product are mutually exclusive; project drives the name).
livemedia-creator --make-iso --iso "$BOOT_ISO" --ks "$KS" --resultdir "$RESULTDIR" \
  --lorax-templates "$HERE/packaging/lorax-templates-99-generic" \
  --project VixzenOS --volid VixzenOS_44_x86_64 2>&1 | tee -a "$LOG"
LMC_RC=${PIPESTATUS[0]:-0}
kill $HTTP_PID 2>/dev/null || true
trap - EXIT
[ "$LMC_RC" -ne 0 ] && log "[WARN] livemedia-creator exited $LMC_RC"
# lorax 44 leaves the image at images/boot.iso inside the result tree
# (not top level) — promote it to a properly named file.
found=$(find "$RESULTDIR" -maxdepth 3 -name '*.iso' 2>/dev/null | head -1)
if [ -n "$found" ]; then
  iso="$RESULTDIR/VixzenOS-0.3-Preview-x86_64.iso"
  [ "$found" = "$iso" ] || mv -f "$found" "$iso"
  log "[OK] ISO: $iso ($(du -h "$iso" | cut -f1))"
  # Implant the md5 frame so the GRUB "Test this media" entry passes.
  # Without it, dracut checkisomd5 fails and the default boot halts.
  if command -v implantisomd5 >/dev/null; then
    implantisomd5 --force "$iso" 2>&1 | tee -a "$LOG" \
      || log "[WARN] implantisomd5 failed (first GRUB entry still boots)"
  else
    log "[SKIP] implantisomd5 not installed (first GRUB entry still boots)"
  fi
else
  log "[FAIL] no ISO produced — see $LOG"; exit 1
fi
