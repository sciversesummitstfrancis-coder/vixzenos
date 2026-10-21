#!/bin/bash
# Install Vixzen Web as a native user app (~/.local, no sudo).
# Usage: ./scripts/install-web.sh [--uninstall]
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$HOME/.local/bin/vixzen-web"
SHARE="$HOME/.local/share/vixzen-web"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"

if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$BIN" "$APPS/os.vixzen.web.desktop" "$ICONS/vixzen-web.svg"
  rm -rf "$SHARE"
  echo "uninstalled."
  exit 0
fi

mkdir -p "$SHARE" "$APPS" "$ICONS" "$HOME/.local/bin"
cp "$HERE/apps/web-browser/vixzen_web.py" "$SHARE/"
cp "$HERE/apps/web-browser/vixzen_search.py" "$HERE/apps/web-browser/blocklist.py" "$SHARE/"
cp "$HERE/apps/web-browser/chrome_import.py" "$SHARE/"
cp "$HERE/apps/web-browser/web_core.py" "$SHARE/"
cp "$HERE/preview/src/design.py" "$SHARE/"
cp "$HERE/assets/branding/vixzen-web.svg" "$ICONS/" 2>/dev/null || true
cp "$HERE/apps/web-browser/vixzen-web" "$BIN"
chmod +x "$BIN" "$SHARE/vixzen_web.py"
cat > "$APPS/os.vixzen.web.desktop" <<EOF
[Desktop Entry]
Name=Vixzen Web
Comment=Native lightweight web browser
Exec=$BIN %U
Icon=vixzen-web
Type=Application
Categories=Network;WebBrowser;
StartupWMClass=vixzen_web
MimeType=text/html;x-scheme-handler/http;x-scheme-handler/https;
EOF
update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
echo "installed: run 'vixzen-web' or find Vixzen Web in your app grid."
