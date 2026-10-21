#!/bin/bash
# Read-only diagnostics for VixzenOS dev. Changes nothing.
echo "=== VixzenOS diag (read-only) ==="
echo "--- CPU ---"; lscpu | grep -E 'Model name|CPU\(s\)|Thread|Core|MHz' | head -6
echo "--- MEM ---"; free -h
echo "--- DISK ---"; df -h / | tail -1
echo "--- OS ---"; cat /etc/fedora-release 2>/dev/null; gnome-shell --version 2>/dev/null
echo "--- SESSION ---"; echo "XDG_SESSION_TYPE=$XDG_SESSION_TYPE GPU: $(lspci 2>/dev/null | grep -i vga | head -1)"
echo "--- TOOLCHAIN ---"
for c in python3 gcc git qemu-kvm livemedia-creator lorax; do
  command -v $c >/dev/null && echo "OK $c" || echo "MISSING $c"
done
python3 -c "import gi; gi.require_version('Gtk','4.0'); gi.require_version('Adw','1'); print('OK GTK4+Adwaita')" 2>&1 | tail -1
