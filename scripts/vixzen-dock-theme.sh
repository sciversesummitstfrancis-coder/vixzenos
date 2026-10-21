#!/bin/bash
# Vixzen dock theme for dash-to-dock — applies instantly, no logout.
# What it does: Vixzen dark bar (#1B1E2A, 92%), indigo running dots,
# Windows-style click=minimize. Fully reversible.
# Usage: ./scripts/vixzen-dock-theme.sh --apply | --revert
P=/org/gnome/shell/extensions/dash-to-dock
case "${1:---apply}" in
  --apply)
    dconf write $P/background-color "'#1B1E2A'"
    dconf write $P/custom-background-color true
    dconf write $P/background-opacity 0.92
    dconf write $P/click-action "'minimize'"
    # NOTE: custom running-dots colors + backlit glow crash this dash-to-dock
    # version (JS ERROR in appIconIndicators.js) — left at stock dots.
    dconf write $P/running-indicator-style "'DOTS'"
    dconf reset $P/dash-max-icon-size
    dconf write $P/extend-height true
    dconf write $P/always-center-icons true
    dconf write $P/autohide false
    dconf write $P/intellihide false
    dconf write $P/dock-fixed true
    dconf reset $P/show-show-apps-button
    dconf write $P/show-windows-preview true
    echo "Vixzen dock theme applied (live)."
    ;;
  --revert)
    for k in background-color custom-background-color click-action \
             running-indicator-style dash-max-icon-size extend-height \
             autohide intellihide dock-fixed show-show-apps-button \
             show-windows-preview always-center-icons; do
      dconf reset $P/$k
    done
    dconf write $P/background-opacity 0.15
    echo "Dock reverted to your previous look."
    ;;
esac
