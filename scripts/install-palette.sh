#!/bin/bash
# Stage the Vixzen Palette release into the ISO tree (vixroot).
#
# Run: sudo ./scripts/install-palette.sh          → ends with PALETTE-OK
#
# What it stages:
#   1. vixzen-shell v3: extension.js + palette.js + fuzzy.js + metadata.json
#      + the org.vixzen.shell keybinding schema (Super+Q), schema compiled.
#   2. vixzen-widgets@vixzen.os — the extension the dconf already enables but
#      the tree never received (fixes the dangling reference GNOME logged).
#   3. background-logo@federahosted.org from the host (host/ISO parity),
#      repointed at the Vixzen logo as a subtle wallpaper watermark.
#   4. Rebuilds the dconf database after editing the keyfile.
# Idempotent: safe to run repeatedly.
set -u
REPO="/home/shonshyjo/Documents/Default Project/vixzenos"
TREE="/home/shonshyjo/Documents/vixzen-surgery/vixroot"
SHELL_DIR="$TREE/usr/share/gnome-shell/extensions/vixzen-shell@vixzen.os"
WIDG_DIR="$TREE/usr/share/gnome-shell/extensions/vixzen-widgets@vixzen.os"
BLOGO_DIR="$TREE/usr/share/gnome-shell/extensions/background-logo@fedorahosted.org"
DCONF_KEYFILE="$TREE/etc/dconf/db/local.d/00-vixzen"

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo."; exit 1; }
[ -d "$TREE/usr/share/gnome-shell/extensions" ] || { echo "Missing ISO tree."; exit 1; }
say(){ echo " - $*"; }

say "staging vixzen-shell v3 (palette + fuzzy + keybinding schema)"
install -d "$SHELL_DIR/schemas"
install -m 644 "$REPO/desktop/shell/extension.js" "$REPO/desktop/shell/palette.js" \
              "$REPO/desktop/shell/fuzzy.js" "$REPO/desktop/shell/metadata.json" "$SHELL_DIR/"
install -m 644 "$REPO/desktop/shell/schemas/org.vixzen.shell.gschema.xml" "$SHELL_DIR/schemas/"
# Extension.getSettings() resolves against the SYSTEM schema source, not the
# extension's own schemas/ dir — without this copy Super+Q throws and is
# swallowed by the addKeybinding try/catch.
install -d "$TREE/usr/share/glib-2.0/schemas"
install -m 644 "$REPO/desktop/shell/schemas/org.vixzen.shell.gschema.xml" \
               "$TREE/usr/share/glib-2.0/schemas/"

say "staging vixzen-widgets (fixes dangling dconf reference)"
install -d "$WIDG_DIR"
install -m 644 "$REPO/desktop/widgets/extension.js" "$REPO/desktop/widgets/metadata.json" "$WIDG_DIR/"

say "staging background-logo from host (parity) + Vixzen logo watermark"
if [ -d /usr/share/gnome-shell/extensions/background-logo@fedorahosted.org ]; then
    install -d "$BLOGO_DIR"
    cp -r /usr/share/gnome-shell/extensions/background-logo@fedorahosted.org/. "$BLOGO_DIR/" \
      || { echo "COPY FAILED: background-logo"; exit 1; }
else
    say "   WARNING: background-logo not present on host — skipping (parity test will flag it)"
fi
install -m 644 "$REPO/assets/boot/logo.png" "$TREE/usr/share/vixzen-branding/logo.png"

say "compiling gsettings schema into the tree"
glib-compile-schemas "$TREE/usr/share/glib-2.0/schemas/" \
  || { echo "SCHEMA COMPILE FAILED"; exit 1; }

say "updating dconf: enable new extensions + watermark settings"
if ! grep -q "'vixzen-shell@vixzen.os'" "$DCONF_KEYFILE"; then
  sed -i "s/^enabled-extensions=\[/enabled-extensions=['vixzen-shell@vixzen.os', /" "$DCONF_KEYFILE"
fi
grep -q "'background-logo@fedorahosted.org'" "$DCONF_KEYFILE" || \
  sed -i "s/'vixzen-widgets@vixzen.os',/'vixzen-widgets@vixzen.os', 'background-logo@fedorahosted.org',/" "$DCONF_KEYFILE"
grep -q "extensions/background-logo\]" "$DCONF_KEYFILE" || cat >> "$DCONF_KEYFILE" <<'EOF'

[org/gnome/shell/extensions/background-logo]
logo-file='/usr/share/vixzen-branding/logo.png'
logo-opacity=0.12
EOF

say "setting system accent to blue (was purple)"
sed -i "s/^accent-color='[^']*'/accent-color='blue'/" "$DCONF_KEYFILE"
grep -q "^accent-color='blue'" "$DCONF_KEYFILE" \
  || { echo "ACCENT UPDATE FAILED"; exit 1; }
dconf compile "$TREE/etc/dconf/db/local" "$TREE/etc/dconf/db/local.d" \
  || { echo "DCONF COMPILE FAILED"; exit 1; }

say "fixing ownership + SELinux labels"
chown -R root:root "$TREE/usr/share/gnome-shell/extensions/vixzen-shell@vixzen.os" \
                   "$TREE/usr/share/gnome-shell/extensions/vixzen-widgets@vixzen.os" \
                   "$TREE/usr/share/glib-2.0/schemas" "$TREE/usr/share/vixzen-branding/logo.png" 2>/dev/null
[ -d "$BLOGO_DIR" ] && chown -R root:root "$BLOGO_DIR"
restorecon -R "$TREE/usr/share/gnome-shell/extensions" "$TREE/usr/share/glib-2.0/schemas" 2>/dev/null || true

say "smoke test"
for f in "$SHELL_DIR/palette.js" "$SHELL_DIR/fuzzy.js" \
         "$WIDG_DIR/extension.js" "$TREE/usr/share/vixzen-branding/logo.png"; do
  [ -f "$f" ] && echo "   OK   ${f#$TREE}" || { echo "   MISS $f"; exit 1; }
done
grep -q "background-logo@fedorahosted.org" "$DCONF_KEYFILE" && echo "   OK   dconf enables background-logo"
[ -f "$TREE/usr/share/glib-2.0/schemas/gschemas.compiled" ] && echo "   OK   gschemas.compiled rebuilt"

say "PALETTE-OK"
