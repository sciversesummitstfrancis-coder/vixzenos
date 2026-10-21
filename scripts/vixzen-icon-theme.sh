#!/bin/bash
# Vixzen icon theme install — live, no logout. Inherits Adwaita, so only
# Vixzen folders/trash/home change; everything else stays stock.
# Usage: ./scripts/vixzen-icon-theme.sh --apply | --revert
HERE="$(cd "$(dirname "$0")/.." && pwd)"
case "${1:---apply}" in
  --apply)
    rm -rf ~/.local/share/icons/Vixzen
    mkdir -p ~/.local/share/icons
    cp -a "$HERE/assets/icons/theme/Vixzen" ~/.local/share/icons/
    gsettings set org.gnome.desktop.interface icon-theme 'Vixzen'
    echo "Vixzen icon theme applied (live). Open Files to see neon folders."
    ;;
  --revert)
    gsettings set org.gnome.desktop.interface icon-theme 'Adwaita'
    rm -rf ~/.local/share/icons/Vixzen
    echo "Icon theme reverted to Adwaita."
    ;;
esac
