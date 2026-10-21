#!/bin/bash
# Vixzen cursor theme — macOS-style pointer (McMojave, vendored GPL-3.0).
# User-scoped, instant for new windows (log out for a full switch).
# Fully reversible (restores your previous theme).
# Usage: ./scripts/vixzen-cursor-theme.sh --apply | --revert
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BK="$HOME/.config/vixzen/cursor-theme.backup"
case "${1:---apply}" in
  --apply)
    mkdir -p "$HOME/.config/vixzen" "$HOME/.local/share/icons"
    [ -f "$BK" ] || gsettings get org.gnome.desktop.interface cursor-theme > "$BK" 2>/dev/null
    rm -rf "$HOME/.local/share/icons/McMojave" "$HOME/.local/share/icons/VixzenHand" "$HOME/.local/share/icons/WhiteSur-cursors"
    cp -a "$HERE/assets/cursors/McMojave" "$HOME/.local/share/icons/"
    cp -a "$HERE/assets/cursors/VixzenHand" "$HOME/.local/share/icons/"
    cp -a "$HERE/assets/cursors/WhiteSur" "$HOME/.local/share/icons/WhiteSur-cursors"
    gsettings set org.gnome.desktop.interface cursor-theme 'WhiteSur-cursors'
    echo "WhiteSur cursor applied (log out for a full switch)."
    ;;
  --revert)
    if [ -f "$BK" ]; then
      prev=$(cat "$BK" | tr -d "'")
      gsettings set org.gnome.desktop.interface cursor-theme "$prev" 2>/dev/null || true
    else
      gsettings set org.gnome.desktop.interface cursor-theme 'Adwaita' 2>/dev/null || true
    fi
    rm -rf "$HOME/.local/share/icons/McMojave" "$HOME/.local/share/icons/VixzenHand" "$HOME/.local/share/icons/WhiteSur-cursors"
    echo "Cursor reverted (see $BK). Log out to finish the switch."
    ;;
esac
