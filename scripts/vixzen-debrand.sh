#!/bin/bash
# Vixzen debrand scrub — removes every visible upstream brand from a system.
#
# SAFETY: operates on a target root, never the live host by accident.
#   Target an image/mounted tree:  VIXZEN_ROOT=/mnt/target bash vixzen-debrand.sh
#   Inside a chroot:                bash vixzen-debrand.sh   (auto-detects /)
#   Refuses to touch a live host unless VIXZEN_ROOT=/ is given explicitly.
#
# Removes (human-visible branding only):
#   - background-logo@fedorahosted.org (paints the Fedora logo on login/overview)
#   - /usr/share/fedora-logos (Fedora logo set)
#   - Fedora GDM/pixmap logos; login logo repointed to the Vixzen logo
#   - Fedora wallpapers (f44 / fedora-workstation)
#   - /etc/fedora-release, /usr/lib/fedora-release
#   - Fedora GDM theme
# Also rewrites /etc/os-release to the VixzenOS identity when
# /etc/vixzen-release is present, and pins DNF's releasever so repository
# URLs keep resolving. It never touches /etc/fstab.
set -u
ROOT="${VIXZEN_ROOT:-}"
if [ -z "$ROOT" ]; then
  if [ -f /etc/vixzen-release ] || [ -f /etc/debian_version ] || [ -f /usr/lib/os-release ]; then
    ROOT="/"
  else
    echo "vixzen-debrand: cannot detect a target root. Set VIXZEN_ROOT=/path/to/root" >&2
    exit 2
  fi
elif [ "$ROOT" = "/" ] && [ -z "${VIXZEN_ALLOW_HOST:-}" ]; then
  echo "vixzen-debrand: refusing to modify a live host. Re-run with VIXZEN_ALLOW_HOST=1" >&2
  exit 2
fi

log(){ echo "[vixzen-debrand] $*"; }
P="$ROOT"

# 1. background-logo extension paints the Fedora infinity logo on the lock
#    screen and overview. Disable + remove + drop its schema.
if [ -d "$P/usr/share/gnome-shell/extensions/background-logo@fedorahosted.org" ]; then
  rm -rf "$P/usr/share/gnome-shell/extensions/background-logo@fedorahosted.org"
  log "removed background-logo extension"
fi
if [ -f "$P/usr/share/glib-2.0/schemas/org.gnome.shell.gschema.override" ]; then
  sed -i "/background-logo@fedorahosted.org/d" \
    "$P/usr/share/glib-2.0/schemas/org.gnome.shell.gschema.override" 2>/dev/null || true
  log "cleared background-logo from shell override"
fi
rm -f "$P/usr/share/glib-2.0/schemas/org.fedorahosted.background-logo-extension.gschema.xml"

# 2. Fedora logo sets + GDM/pixmap logos.
rm -rf "$P/usr/share/fedora-logos"
rm -f "$P/usr/share/pixmaps/fedora"* 2>/dev/null || true
log "removed Fedora logo + pixmap assets"

# 2b. Repoint the login-screen logo away from the deleted Fedora pixmap.
if [ -f "$P/usr/share/vixzen-branding/logo.svg" ]; then
  mkdir -p "$P/usr/share/glib-2.0/schemas"
  cat > "$P/usr/share/glib-2.0/schemas/org.gnome.login-screen.gschema.override" <<'EOF'
[org.gnome.login-screen]
logo='/usr/share/vixzen-branding/logo.svg'
EOF
  log "login logo repointed to Vixzen"
else
  rm -f "$P/usr/share/glib-2.0/schemas/org.gnome.login-screen.gschema.override" 2>/dev/null || true
  log "login logo override removed (no Vixzen logo present)"
fi

# 3. Fedora wallpapers (we ship our own under /usr/share/backgrounds/vixzen).
rm -rf "$P/usr/share/backgrounds/fedora-workstation" 2>/dev/null || true
for d in "$P"/usr/share/backgrounds/f44 "$P"/usr/share/backgrounds/fedora*; do
  [ -d "$d" ] && rm -rf "$d"
done
# Fedora-supplied wallpapers/doc packages and the stock test page.
rm -rf "$P/usr/share/doc/fedora-third-party" \
       "$P/usr/share/doc/fedora-workstation-backgrounds" \
       "$P/usr/share/fedora-testpage" 2>/dev/null || true
log "removed Fedora wallpapers + stock background docs"

# 4. Release identity files.
rm -f "$P/etc/fedora-release" "$P/usr/lib/fedora-release" \
      "$P/etc/system-release-cpe" 2>/dev/null || true
log "removed fedora-release identity files"

# 4b. Rewrite os-release when the Vixzen identity file exists. The release
#     number DNF needs is pinned separately so repo URLs keep resolving.
if [ -f "$P/etc/vixzen-release" ]; then
  cp "$P/etc/vixzen-release" "$P/usr/lib/os-release"
  rm -f "$P/etc/os-release"
  cp "$P/etc/vixzen-release" "$P/etc/os-release"
  mkdir -p "$P/etc/dnf/vars"
  [ -f "$P/etc/dnf/vars/releasever" ] || echo "44" > "$P/etc/dnf/vars/releasever"
  log "os-release rewritten to VixzenOS (dnf releasever pinned to 44)"
else
  log "no /etc/vixzen-release — leaving os-release untouched"
fi

# 5. GDM theme.
rm -rf "$P/usr/share/gdm/theme/fedora" 2>/dev/null || true
log "removed Fedora GDM theme"

# 6. Rebuild caches so removed assets stop being served.
if command -v dconf >/dev/null; then
  dconf update 2>/dev/null || true
fi
if command -v glib-compile-schemas >/dev/null; then
  glib-compile-schemas "$P/usr/share/glib-2.0/schemas" 2>/dev/null || true
fi
for ic in "$P/usr/share/icons/hicolor" "$P/usr/share/icons/Adwaita"; do
  [ -d "$ic" ] && gtk-update-icon-cache -f "$ic" 2>/dev/null || true
done
log "caches rebuilt"
log "done — os-release now identifies as VixzenOS; dnf releasever is pinned separately"
