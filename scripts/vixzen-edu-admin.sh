#!/bin/bash
# Vixzen Edu admin helper — school lockdown switches. Runs as ROOT via pkexec
# from Vixzen Settings ("School Admin" page) or directly with sudo.
# Usage: vixzen-edu-admin.sh net-off|net-on|net-status|store-lock|store-unlock|store-status
# Students (non-wheel) cannot re-enable: polkit rules gate NetworkManager and
# PackageKit to admin users (see packaging/edu-polkit/). Reversible always.
set -u
STORE_RULE=/etc/polkit-1/rules.d/49-vixzen-edu-store.rules
SRC_RULE=/usr/share/vixzen-edu/49-vixzen-edu-store.rules

case "${1:-status}" in
  net-off)
    nmcli networking off && echo "Edu: internet OFF (admin can re-enable)" ;;
  net-on)
    nmcli networking on && echo "Edu: internet ON" ;;
  net-status)
    if [ "$(nmcli -t -f STATE general 2>/dev/null)" = "connected" ]; then
      echo "on"
    else
      nmcli -t -f STATE general 2>/dev/null | grep -q connected && echo "on" || echo "off"
    fi ;;
  store-lock)
    mkdir -p "$(dirname "$STORE_RULE")"
    cp "$SRC_RULE" "$STORE_RULE" 2>/dev/null || {
      echo "Edu: rule source missing ($SRC_RULE)"; exit 1; }
    echo "Edu: software store LOCKED (admin auth required to install)" ;;
  store-unlock)
    rm -f "$STORE_RULE" && echo "Edu: software store UNLOCKED" ;;
  store-status)
    [ -f "$STORE_RULE" ] && echo "locked" || echo "unlocked" ;;
  *)
    echo "Usage: $0 net-off|net-on|net-status|store-lock|store-unlock|store-status"
    exit 2 ;;
esac
