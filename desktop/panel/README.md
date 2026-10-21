# Vixzen Host Panel (dev/test tool — never ships)

A real bottom bar on a live desktop via gtk4-layer-shell, for trying bar
ideas without logging out. It is NOT part of VixzenOS: the ISO never
installs it, and the default taskbar is dash-to-dock (see
`docs/ARCHITECTURE.md` §6).

> Status 2026-10-10: does NOT anchor on GNOME/Mutter (no layer-shell
> protocol — floating window only). Kept for wlroots-based testing.
> For GNOME widgets use the `vixzen-widgets` shell extension instead.

Run: `./run-panel.sh` — Stop: right-click → Quit.
