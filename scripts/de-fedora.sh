#!/bin/bash
# Vixzen de-Fedora scrub — removes every visible Fedora brand from a system.
#
# SAFETY: operates on a target root, never the live host by accident.
#   Target an image/mounted tree:  VIXZEN_ROOT=/mnt/target bash de-fedora.sh
#   Inside a chroot:                bash de-fedora.sh   (auto-detects /)
#   Refuses to touch a live host unless VIXZEN_ROOT=/ is given explicitly.
#
# Removes (human-visible branding only):
#   - background-logo@fedorahosted.org (paints the Fedora logo on login/overview)
#   - /usr/share/fedora-logos (Fedora logo set)
#   - Fedora GDM/pixmap logos; login logo repointed to the Vixzen logo
#   - Fedora wallpapers (f44 / fedora-workstation)
#   - /etc/fedora-release, /usr/lib/fedora-release
#   - Fedora GDM theme
# Keeps: the "fedora" ID in /etc/os-release (dnf + third-party repos key off
# it) and /etc/fstab. Both are invisible to users.
set -u
ROOT="${VIXZEN_ROOT:-}"
if [ -z "$ROOT" ]; then
  if [ -f /etc/vixzen-release ] || [ -f /etc/debian_version ] || [ -f /usr/lib/os-release ]; then
    ROOT="/"
  else
    echo "de-fedora: cannot detect a target root. Set VIXZEN_ROOT=/path/to/root" >&2
    exit 2
  fi
elif [ "$ROOT" = "/" ] && [ -z "${VIXZEN_ALLOW_HOST:-}" ]; then
  echo "de-fedora: refusing to modify a live host. Re-run with VIXZEN_ALLOW_HOST=1" >&2
  exit 2
fi

log(){ echo "[de-fedora] $*"; }
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
rm -f "$P/etc/fedora-release" "$P/usr/lib/fedora-release" 2>/dev/null || true
log "removed fedora-release identity files"

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
log "done — the remaining 'fedora' ID in os-release is intentional (dnf/repo compatibility)"
