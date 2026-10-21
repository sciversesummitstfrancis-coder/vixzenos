#!/bin/bash
# Install Vixzen Blink (EXPERIMENTAL) to ~/.local. Needs PyQt6 + PyQt6-WebEngine:
#   python3 -m pip install --user PyQt6 PyQt6-WebEngine
# Usage: ./scripts/install-blink.sh [--uninstall]
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
if ! python3 -c "from PyQt6 import QtWebEngineWidgets" 2>/dev/null \
   && ! python3 -c "from PySide6 import QtWebEngineWidgets" 2>/dev/null; then
  echo "missing Qt WebEngine bindings. Run first:" >&2
  echo "  python3 -m pip install --user PyQt6 PyQt6-WebEngine" >&2
  exit 1
fi
BIN="$HOME/.local/bin/vixzen-blink"
SHARE="$HOME/.local/share/vixzen-blink"
APPS="$HOME/.local/share/applications"
if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$BIN" "$APPS/os.vixzen.blink.desktop"
  rm -rf "$SHARE"
  echo "uninstalled."
  exit 0
fi
mkdir -p "$SHARE" "$APPS" "$HOME/.local/bin"
cp "$HERE/apps/web-browser-blink/vixzen_blink.py" "$SHARE/"
cp "$HERE/apps/web-browser/vixzen_search.py" "$SHARE/"
cp "$HERE/apps/web-browser/blocklist.py" "$SHARE/"
cp "$HERE/apps/web-browser/web_core.py" "$SHARE/"
cp "$HERE/apps/web-browser-blink/vixzen-blink" "$BIN"
chmod +x "$BIN"
sed "s|^Exec=.*|Exec=$BIN %U|" "$HERE/apps/web-browser-blink/os.vixzen.blink.desktop" \
  > "$APPS/os.vixzen.blink.desktop"
update-desktop-database "$APPS" 2>/dev/null || true
echo "installed: run 'vixzen-blink' (experimental Blink engine)."
