# VixzenOS Milestones — the road to a working OS on any PC

Legend: ✅ done · 🔶 now · ⬜ next. Owner: AI / YOU / TOGETHER.

## M0 — Inspect & decide ✅ (AI)
Host measured (i5-6200U, 8 GB, HD 520, Fedora 44, Wayland), stack chosen
(GTK4+Libadwaita preview, GNOME extension shell, livemedia ISO). Doc: `docs/ARCHITECTURE.md`.

## M1 — Preview + identity ✅ (AI)
Interactive mock (taskbar, launcher, files/settings mocks, themes, perf
modes), Vixzen tokens (`design.py`), logo, wallpapers. Verified by smoke tests.

## M2 — Live theming ✅ (TOGETHER)
Dock themed + centered + full-width, Vixzen icon pack (folders, 7 apps,
grid badge), shell glass theme, signature wallpaper default, logo + search
pins, power + start menus, accent picker. All one-command reversible
(`scripts/vixzen-*.sh --revert`). Proven on the live desktop.

## M3 — Real components ✅ code-complete, ⬜ runtime-proving (AI + YOU)
Vixzen Files (thumbnails, trash, copy/paste), Settings (real prefs pages),
one-piece shell bar + attached menu + magnification (syntax-checked, API-
proven, staged). Runtime proof needs one login (bar) — pending your call.

## M4 — ISO content complete ✅ (AI)
- Stage transport, zero-Fedora boot, apps + bar + icons + themes + pins,
  login-screen theme block (simulated-verified) — `./build-vixzenos.sh --check-only` green.

## M5 — First bootable ISO ✅ dock ISO boots to login (TOGETHER)
- Pipeline built 2.8G ISO; hand-repaired rescue ISO (`VixzenOS-0.3-dock`)
  boots past all gates in QEMU: EFI ✓, live mount ✓, GDM login ✓, burst
  wallpaper ✓. Proven via serial logs + screenshots.
- Taskbar decided: dash-to-dock compact dock is THE bar (ARCHITECTURE §6).
- Still open: desktop screenshot after login, hardware USB test (→ M6).

## M6 — Real hardware ⬜ (YOU, AI on call)
- USB Live boot on your Dell (try-without-install, Fedora untouched): Wi-Fi, sound, display, suspend
- Second machine if available (driver check); Secure Boot on/off check
- Exit: hardware checklist green in `docs/HARDWARE.md` (to be created).

## M7 — Updates & release 🔶 channel live, publish pending (TOGETHER)
- VixzenOS is now a **real RPM channel**: vixzenos-apps / -theme / -cursor /
  -cli / -release, built + verified locally (`scripts/vixzen-rpm-build.sh`),
  consumable by dnf exactly like any distro repo (verified: dnf lists all
  five from a local repo).
- Client: `sudo vixzen-repo-setup.sh` adds the channel; `vix update check`
  and `vix update history` report status.
- Pending (needs your accounts): create the COPR project `vixzen/vixzenos`,
  then `./scripts/vixzen-rpm-build.sh --publish`. See `docs/RELEASES.md`.
- Also done: de-Fedora scrub (`scripts/de-fedora.sh`) runs in every build and
  in the release package; `.gitignore` keeps build output out of GitHub.

## M8 — Refinement (later)
Anaconda installer rebrand, Plymouth polish, accessibility pass, perf budgets
measured on target hardware, M6 re-test.

## Browser track → `docs/BROWSER_MILESTONES.md` (WB0 ✅ base done, WB1 🔶 next)

## Standing rules
- Show-before-apply on the live system; every live change reversible.
- ISO work never touches the host (verified per change).
- No perf claim without measurement; no "done" without a boot or a screenshot.
