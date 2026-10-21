# VixzenOS Architecture (Milestone 1 decision record)

## 1. Host facts (measured 2026-09-24)
- CPU: Intel i5-6200U (2C/4T, up to 2.8 GHz) — verified via `lscpu`
- RAM: 7.4 GiB total, ~2.7 GiB available (GNOME idle) — `free -h`
- Disk: 379 GiB free on `/` — room for builds
- OS: Fedora Linux 44 Workstation, kernel 7.1.10-200.fc44, GNOME Shell 50.5
- Session: Wayland (`XDG_SESSION_TYPE=wayland`), GPU: Intel HD Graphics 520
- Toolchain present: `python3.14`, `gcc`, `git`, `qemu-kvm`, `livemedia-creator`,
  `lorax`, `livecd-creator`, `grub2-mkrescue`, GTK 4.22.5 + libadwaita 1.9.4 + PyGObject
- Existing work: `../MyOS/` — Tkinter desktop prototype + shared `commands.py`
  engine + 1.4 MB bootable initramfs (QEMU-verified). Preserved, not deleted.

## 2. Stack decision (why, in simple language)
| Layer | Choice | Why for this hardware |
|---|---|---|
| Preview prototype | **Python + GTK4 + Libadwaita** (`preview/src/`) | Already installed, Wayland-native, ~30–50 MB RAM (vs ~300 MB+ Electron), CSS theming + `Adw` animations, same toolkit reusable for real apps. No new heavy deps. |
| Real taskbar/shell | **GNOME Shell extension** (`desktop/shell/`, Milestone 3) | Reuses Mutter/GNOME compositing (GPU-accelerated, tested on HD 520) instead of writing a compositor from scratch. Falls back gracefully. |
| Real file manager / settings | **GTK4 standalone apps** (`apps/`) | Share design tokens with preview; can run inside GNOME today, inside Vixzen session later. |
| Base OS / ISO | **Fedora Workstation + livemedia-creator kickstart** (`packaging/vixzenos.ks`) | Official Fedora path, best driver coverage, `lorax`/`livemedia-creator` already on disk. Atomic/image-based rejected for now: heavier rebuilds, harder for a beginner to debug. |
| What we avoid | Electron, Qt/QML full DE, custom Wayland compositor | Too much RAM / disk / maintenance for 8 GB + HD 520 and a solo beginner. |

Tkinter (MyOS) taught us the window-manager logic cheaply, but it looks dated
and themes poorly — so we graduate the *ideas* (taskbar model, command engine)
to GTK4 rather than copying the code verbatim.

## 3. Design tokens (original Vixzen identity)
- Accent indigo `#4F46E5` (dark theme: `#7C7CFF`), secondary cyan `#06B6D4`
- Light: bg `#F2F3F7`, fg `#1A1D29`, taskbar `#E8EAF2`
- Dark: bg `#12141C`, fg `#E8EAF2`, taskbar `#1B1E2A`
- Radius 10px, 8pt spacing grid, system font (Cantarell), vector SVG icons.
- No proprietary assets. No heavy blur/3D by default.

## 4. Milestone roadmap
1. **Inspect & Plan** (done) — this file + `BUILDING.md` + `PERFORMANCE.md`.
2. **Preview** (now) — `preview/src/vixzen_preview.py`: taskbar, launcher,
   mock files/settings, themes, 3 performance modes.
3. **Functional components** — GNOME extension shell + real GTK file-manager
   and settings; keyboard nav; app launching via `.desktop` files.
4. **Performance** — profile with `scripts/diag.sh`, enforce budgets.
5. **ISO** — `build-vixzenos.sh` + `packaging/vixzenos.ks` via
   `livemedia-creator`; test in QEMU (only if RAM allows).
6. **Refinement** — a11y, consistency, docs, release prep.

## 5. Safety rules
- Preview never edits real files (mock data only; file mock lists `~` read-only).
- Build script never partitions, never touches bootloader without explicit flag.
- All perf claims require measurement (`PERFORMANCE.md` budgets).

## 6. Taskbar decision (2.0 audit, 2026-09-30 — FINAL)
THE taskbar is **dash-to-dock, compact centered dock** (macOS-style,
`extend-height=false`, minimize-on-click). Rationale: mature upstream,
zero maintenance, user explicitly chose the dock look over our bar.
- `vixzen-shell` extension: installed, OFF, documented alternative for the
  bar + Start Menu + magnification workflow. Enable manually; never default.
- `hidetopbar`: ON in ISO (single-bar look, no double bars).
- `desktop/panel/` (layer-shell): dev/test tool only. Never ships in ISO.
- Preview mock bar: prototype inside the preview app only.
Revisit only with user approval + a migration note here.

## 7. Two-engine browser strategy (2026-10-02)
- Default: **Vixzen Web** (WebKitGTK, ~168 MB, GTK Liquid Glass).
- Fallback: **upstream Chromium** in the ISO (`chromium` in `packaging/vixzenos.ks`) + **Vixzen Blink v0.1** (`apps/web-browser-blink/`, QtWebEngine/Chrome-140, experimental, not in ISO yet). Shares `~/.config/vixzen-web/` data and Vixzen Search with Vixzen Web.
