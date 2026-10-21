#!/bin/bash
# Vixzen host features — visible, user-scoped, reversible. No sudo, no logout
# needed except: vixzen-shell bar + hide-top-bar activate on next login.
# Usage: ./scripts/vixzen-host-features.sh --apply | --revert
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:---apply}"
BK="$HOME/.config/vixzen/host-features.backup"

backup_once() {
  [ -f "$BK" ] && return 0
  mkdir -p "$(dirname "$BK")"
  { echo "dynamic-workspaces=$(gsettings get org.gnome.mutter dynamic-workspaces)"
    echo "font=$(gsettings get org.gnome.desktop.interface font-name)"
    echo "docfont=$(gsettings get org.gnome.desktop.interface document-font-name)"
    echo "weekday=$(gsettings get org.gnome.desktop.interface clock-show-weekday)"
    echo "custom=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)"
  } > "$BK" 2>/dev/null
  echo "Backed up current values to $BK"
}

set_binding() { # path name command binding
  gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$1" name "$2" 2>/dev/null
  gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$1" command "$3" 2>/dev/null
  gsettings set "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:$1" binding "$4" 2>/dev/null
}

case "$MODE" in
  --apply)
    backup_once
    echo "== window management =="
    gsettings set org.gnome.mutter edge-tiling true
    gsettings set org.gnome.mutter dynamic-workspaces false   # fixed 4 workspaces
    gsettings set org.gnome.desktop.wm.preferences num-workspaces 4
    echo "== keyboard shortcuts (appended, jcode bindings kept) =="
    set_binding /org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-files/ 'Vixzen Files' 'nautilus' '<Super>e'
    set_binding /org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-terminal/ 'Vixzen Terminal' 'ptyxis' '<Super>t'
    cur=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings)
    for p in vixzen-files vixzen-terminal; do
      full="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/$p/"
      echo "$cur" | grep -q "$p" || cur=$(python3 -c "import ast,sys; l=ast.literal_eval(sys.argv[1]); l.append(sys.argv[2]); print(l)" "$cur" "$full")
    done
    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$cur"
    echo "== fonts and details =="
    gsettings set org.gnome.desktop.interface font-name 'Cantarell 11'
    gsettings set org.gnome.desktop.interface document-font-name 'Cantarell 12'
    gsettings set org.gnome.desktop.interface clock-show-weekday true
    echo "== vixzen-shell bar (left disabled: not wanted on host) =="
    mkdir -p "$HOME/.local/share/gnome-shell/extensions/vixzen-shell@vixzen.os"
    cp "$HERE/desktop/shell/extension.js" "$HERE/desktop/shell/metadata.json" \
       "$HOME/.local/share/gnome-shell/extensions/vixzen-shell@vixzen.os/"
    chmod 644 "$HOME/.local/share/gnome-shell/extensions/vixzen-shell@vixzen.os/"* 2>/dev/null || true
    echo "Bar files synced but NOT enabled (host uses dash-to-dock only)."
    ;;
  --revert)
    echo "== reverting =="
    [ -f "$BK" ] && {
      # shellcheck disable=SC1090
      while IFS='=' read -r k v; do
        case "$k" in
          dynamic-workspaces) gsettings set org.gnome.mutter dynamic-workspaces "$v" ;;
          font) gsettings set org.gnome.desktop.interface font-name "$v" ;;
          docfont) gsettings set org.gnome.desktop.interface document-font-name "$v" ;;
          weekday) gsettings set org.gnome.desktop.interface clock-show-weekday "$v" ;;
          custom) gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$v" ;;
        esac
      done < "$BK"
      gsettings reset-recursively "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-files/" 2>/dev/null
      gsettings reset-recursively "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/vixzen-terminal/" 2>/dev/null
      echo "Restored from $BK"
    } || echo "No backup found; nothing to revert."
    gnome-extensions disable vixzen-shell@vixzen.os 2>/dev/null || true
    echo "Reverted (bar disappears after logout/login)."
    ;;
  *) echo "Usage: $0 --apply | --revert"; exit 2 ;;
esac
