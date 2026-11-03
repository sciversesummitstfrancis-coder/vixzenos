# Vixzen Palette — keyboard-first command surface

**Status:** flagship feature, v1.0 — implemented and unit-tested.
**Scope:** one focused idea done properly — *search anything on the desktop, act on it without the mouse.*

## What it is

Press `Super+Q` (or click the magnifier next to the Vixzen badge on the bar) and a
single palette opens. Type fuzzily; results arrive from four providers:

| Provider | Results | Enter | Ctrl+Enter |
|----------|---------|-------|------------|
| Windows | every open window, any workspace | focuses it (`Main.activateWindow`) | sends it to the next workspace |
| Applications | launchable desktop apps | launches it | — |
| Actions | `Dark Mode: On/Off`, `Do Not Disturb: On/Off` | toggles (per-user GSettings) | — |
| Workspaces | every workspace but the current one | switches to it | — |

The same fuzzy matcher upgraded the existing Start Menu search: `'vwm'` now finds
*Vixzen Web Menu*, prefixes outrank scattered matches, matched characters render
**bold**.

## Why it fits VixzenOS's rules

- **Zero idle cost.** The palette builds no actors, runs no timers, and polls
  nothing while closed. Providers gather state once per open. The matcher scored
  200 candidates × 3 queries in **2 ms** (budget: 50 ms) on the target machine class.
- **Saver mode honored.** `perf: saver` disables the open animation, matching the
  existing Vixzen performance rules.
- **Permission boundary.** No subprocesses, no DBus, no portals, no polkit. The
  only state changes are two per-user GSettings toggles. Nothing privileged can
  be invoked from the palette, so nothing privileged can be fuzzied into.
- **Failure states.** A provider that throws contributes no rows; zero results
  shows a status line, never a dead panel.

## Files (all new or changed in this release)

| File | Role |
|------|------|
| `desktop/shell/fuzzy.js` | pure-JS fuzzy scorer + Pango-safe highlighting; no GNOME imports, fully unit-testable |
| `desktop/shell/palette.js` | the palette UI + providers + keyboard handling |
| `desktop/shell/extension.js` | bar button, `Super+Q` keybinding wiring, menu search upgrade, disable cleanup |
| `desktop/shell/metadata.json` | v3; `settings-schema: org.vixzen.shell` |
| `desktop/shell/schemas/org.vixzen.shell.gschema.xml` | the `open-palette` keybinding schema |
| `scripts/install-palette.sh` | stages everything into the ISO tree (sudo, idempotent) |
| `tests/js/fuzzy_smoke.js` | gjs harness — runs the real module, 12 cases + benchmark |
| `tests/test_palette_fuzzy.py` | pytest wrapper + metadata/schema/wiring/permission tests |
| `docs/PALETTE.md` | this document |

Riding along (audit findings):
- `desktop/widgets/` staged into the ISO tree — the dconf already enabled
  `vixzen-widgets@vixzen.os`; the extension had never been copied (GNOME logged
  an error every login).
- the upstream background-logo extension (now enabled on the host) staged
  from the host and **repointed at the Vixzen logo** as a 12% opacity
  wallpaper watermark — the parity test passes and the upstream mark stays
  scrubbed.

## Launch, configure, disable, uninstall

- **Launch:** `Super+Q` (configurable). The magnifier button on the bar only
  exists when the bar is enabled (see below).
- **Configure:** `gsettings set org.vixzen.shell open-palette "['<Super>q']"`
  (or clear it to disable the shortcut — the bar button keeps working).
- **Bar on/off:** `gsettings set org.vixzen.shell show-bar true|false`.
  Default is **false** on VixzenOS: `dash-to-dock` owns the taskbar and this
  extension ships only the Palette, so there is never a second taskbar. Set it
  to `true` to swap the dock for the Vixzen bar + Start Menu.
- **Disable entirely:** toggle *Vixzen Shell* off in Extensions, or
  `gnome-extensions disable vixzen-shell@vixzen.os`.
- **Uninstall:** `sudo ./scripts/install-palette.sh` stages *into* the tree, so
  uninstall = remove `vixzen-shell@vixzen.os` from the tree's extensions dir and
  drop the uuid from `etc/dconf/db/local.d/00-vixzen` — the staging script is
  additive and idempotent, nothing else owns these files.

## Tests actually run (and results)

| Suite | Command | Result |
|-------|---------|--------|
| Palette suite | `python3 -m pytest tests/test_palette_fuzzy.py -q` | **6/6 passed** |
| Full repo suite | `python3 -m pytest tests/ -q` | **47/48 passed** — the one failure was the host-parity test catching the missing `background-logo` extension (pre-existing; fixed in this release by the kickstart + staging changes) |
| Fuzzy benchmark | inside the gjs harness | 2 ms for 600 scoring operations |
| Schema strictness | `glib-compile-schemas --strict` | clean compile |

## Honest limitations

1. **Not yet live-tested in the shell.** The modules were written against the
   same API set as the already-booted vixzen-shell v2 (St, Clutter, Meta, Main),
   but Wayland requires a session reload to load the updated extension — the
   live proof happens in the QEMU VM boot test with the next ISO repack
   (screendump will be attached to the release).
2. **Ctrl+Enter only moves windows forward** one workspace; it does not pick a
   destination. That's a deliberate v1 scope cut, not a bug.
3. **Actions are two toggles**, not a full settings surface — deliberately.
   Palette actions stay user-level only; anything privileged stays out by design.
4. **App results are capped at 200** (alphabetical) to keep matching instant;
   beyond that, narrow the query.

## Demonstration plan (5 minutes)

1. Boot the rebuilt ISO in QEMU (or install vixzen-shell v3 on the host).
2. Press `Super+Q` → type `fir` → Firefox window focuses (windows provider).
3. Type `vix` → Vixzen apps + Dark Mode appear (fuzzy + actions).
4. Highlight a window, press `Ctrl+Enter` → watch it hop to the next workspace.
5. Open the Start Menu → type `vwm`-style abbreviations → menu now fuzzy-matches.
