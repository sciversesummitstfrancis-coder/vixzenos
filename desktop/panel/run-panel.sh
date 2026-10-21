#!/bin/bash
# Launch the Vixzen host panel (bottom bar on your real desktop).
# Works around the gtk4-layer-shell linker quirk via LD_PRELOAD.
# Stop: right-click the bar → Quit, or Ctrl+C here.
cd "$(dirname "$0")/../.."
export LD_PRELOAD=/usr/lib64/libgtk4-layer-shell.so.0
exec python3 desktop/panel/vixzen_panel.py "$@"
