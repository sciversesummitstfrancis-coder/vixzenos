# Vixzen Shell (alternative taskbar — NOT the default)

The default VixzenOS taskbar is **dash-to-dock, compact centered dock**
(decided 2026-09-30, see `docs/ARCHITECTURE.md` §6). This extension is the
documented alternative: bottom bar + attached Start Menu + magnification.
It ships installed-but-OFF in the ISO; enable it manually if you prefer it
over the dock. Replaces nothing; breaks nothing when disabled.

Reuses GNOME/Mutter compositing instead of a custom compositor (right call for
HD 520 + solo maintenance). Preview stays mock; this extension becomes the real
bottom taskbar.

## Now (stub)
`extension.js` + `metadata.json` add a "◈ Vixzen" label to the top panel so the
install/enable cycle can be tested without breaking the session.

## Next (Milestone 3 full)
- Bottom panel: launcher, pinned apps (`Gio.AppInfo`), running indicators via
  `Shell.AppSystem`, clock, quick settings.
- Respect Saver/Balanced/Enhanced (no animations in Saver).
- Test: `gnome-extensions enable vixzen-shell@vixzen.os`, log out/in on Wayland.

## Safety
Extension only — never touches disks, bootloader, or other users' sessions.
