# VixzenOS — Lightweight, Graphical Linux Desktop

A Windows-familiar desktop (bottom dock, Start menu, Vixzen Files) with an
original neon visual identity, built as a live ISO on a Fedora base. Optimized
for low-spec hardware (primary target: Dell Latitude 3570, i5-6200U, 8 GB RAM,
Intel HD 520).

> **Status: 0.3 Preview.** Working bootable live ISO; Personal + Edu editions;
> `vix` command center; Vixzen Files / Settings / Power / Browser apps.

## What this is

- **VixzenOS** — an independent Linux distribution built on Fedora packages.
  All artwork, branding, apps and workflows in this repo are original work.
  Fedora, GNOME, and other upstream projects remain the copyright of their
  respective owners; this project is not affiliated with or endorsed by them.

## Get VixzenOS

**Live ISO (try without installing):**
- Releases: `https://github.com/sciversesummitstfrancis-coder/vixzenos/releases`
- Verify: `sha256sum -c SHA256SUMS.txt`
- Write to USB: `sudo dd if=VixzenOS-0.3-x86_64.iso of=/dev/sdX bs=4M status=progress oflag=sync`

**Packages (update channel):**
```bash
sudo vixzen-repo-setup.sh
sudo dnf install vixzenos-release
```

## Quick start

```bash
./scripts/diag.sh                      # hardware + toolchain check (read-only)
python3 preview/src/vixzen_preview.py  # interactive UI prototype
./build-vixzenos.sh --check-only        # validate build prerequisites
```

## Layout

```
vixzenos/
├── build-vixzenos.sh    # reproducible ISO build entry point
├── packaging/           # kickstarts (personal + edu), lorax templates, polkit
├── apps/                # Vixzen apps: files, settings, power, browser, CLI
├── desktop/             # shell extensions (bar, widgets, effects) + vendored
├── assets/              # icons, cursors, themes, wallpapers, boot art
├── scripts/             # theming, branding, updates, de-branding scrub
├── shared/              # vixzen_core: shared config + styling for all apps
├── tests/               # headless test suite (29 checks)
├── docs/                # architecture, branding, milestones, performance
└── website/             # project site
```

## Editions

| Edition | Build | Purpose |
|---|---|---|
| Personal | `sudo ./build-vixzenos.sh ./build/boot.iso` | daily driver |
| Edu | `VXZ_KS=packaging/vixzenos-edu.ks sudo -E ./build-vixzenos.sh ./build/boot.iso` | classroom lockdown (admin internet switch, store lock) |

## Performance modes

1. **Battery Saver** — no blur/transparency, animations off.
2. **Balanced** (default) — short fade/slide ≤200 ms, flat surfaces.
3. **Enhanced** — subtle shadows + transitions, only if GPU allows.
4. **Insane** — 600 ms cinematic mode (opt-in).

Measure, don't guess: see `docs/PERFORMANCE.md`.
