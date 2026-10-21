#!/bin/bash
# Vixzen shell theme install — top bar + controls in Vixzen identity.
# Live, no logout (user-theme extension must already be discovered).
# Usage: ./scripts/vixzen-shell-theme.sh --apply | --revert
HERE="$(cd "$(dirname "$0")/.." && pwd)"
UUID="user-theme@gnome-shell-extensions.gcampax.github.com"
case "${1:---apply}" in
  --apply)
    mkdir -p ~/.local/share/themes/Vixzen/gnome-shell
    cp "$HERE/assets/shell-theme/gnome-shell.css" ~/.local/share/themes/Vixzen/gnome-shell/
    gsettings set org.gnome.shell.extensions.user-theme name 'Vixzen'
    gnome-extensions enable "$UUID"
    echo "Vixzen shell theme applied (live)."
    ;;
  --revert)
    gsettings set org.gnome.shell.extensions.user-theme name ''
    gnome-extensions disable "$UUID"
    echo "Shell theme reverted to stock GNOME."
    ;;
esac
