# AGENTS.md — VixzenOS

You are working in **VixzenOS**, an independent Linux distribution: a
Windows-familiar desktop (bottom dock, Start menu, Vixzen Files) with an original
neon identity, shipped as a bootable live ISO with its own release identity and
kernel release tag. Current status: **0.3 Preview**.

Read this before touching anything. It encodes the traps that cost real time here.

---

## 1. The one rule that matters most

**Edit the canonical tree at repo root. Never edit `packaging/rpm/`.**

`packaging/rpm/SOURCES/vixzen-tree/**` and `packaging/rpm/build/**` are **staging
copies** made with `cp -a` by `scripts/vixzen-rpm-build.sh`. They are gitignored
and blown away on every RPM build. Editing there produces changes that silently
vanish and that nobody will ever see in a diff.

- ✅ `apps/file-manager/vixzen_files.py`
- ❌ `packaging/rpm/SOURCES/vixzen-tree/apps/file-manager/vixzen_files.py`

Same applies to `build/` (ISO output), `*.log`, `__pycache__/`, `.pytest_cache/`.
All gitignored. Never commit them, never read them as source of truth.

## 2. Stack & target hardware

| Layer | Choice |
|---|---|
| Apps | Python 3.14 + GTK4 / Libadwaita (PyGObject), pure stdlib otherwise |
| Shell | GNOME Shell extension (JS) — `desktop/shell/` |
| ISO / OS | VixzenOS kickstart + livemedia-creator/lorax on a Fedora-compatible package base |
| Tooling | bash scripts |
| Website | vanilla HTML/CSS/JS (no framework, no build step) |

**Target hardware is a 2015 low-spec laptop**: Dell Latitude 3570, i5-6200U
(2C/4T), 8 GB RAM, Intel HD 520, Wayland. Every decision is downstream of this.

**Explicitly rejected in `docs/ARCHITECTURE.md` — do not reintroduce:** Electron,
Qt/QML as a full DE, or writing a custom Wayland compositor. If a change needs a
heavy dependency or a large memory footprint, it is almost certainly wrong.

## 3. Layout

```
build-vixzenos.sh    ISO build entry point (safe by default)
packaging/           kickstarts (personal + edu), lorax templates, polkit rules, RPM SPECS
apps/                GTK4 apps: files, settings, power, browser (+ blink), vix CLI
desktop/             GNOME Shell extension: panel, shell (fuzzy.js, palette.js), widgets
assets/              icons, cursors, themes, wallpapers, boot art  (73 MB — do not commit raster churn)
scripts/             theming, branding, updates, publish, RPM build, de-branding scrub
shared/vixzen_core/  the shared library every app imports — see §5
tests/               headless pytest suite
preview/             interactive UI prototype
website/             static site
docs/                ARCHITECTURE, BUILDING, BRANDING, PALETTE, PERFORMANCE, PUBLISH, RELEASES, WINDOWS
```

`packaging/` is 330 MB and `assets/` 73 MB — use targeted globs, never a repo-wide
`grep -r` or `find` without an exclude.

## 4. Commands

```bash
./scripts/diag.sh                        # hardware + toolchain check (read-only, safe)
python3 preview/src/vixzen_preview.py    # interactive UI prototype
python3 -m pytest tests/ -q              # full headless suite

./build-vixzenos.sh --check-only         # SAFE: validate prerequisites, smoke-test every app
sudo ./build-vixzenos.sh                 # full ISO build (slow, needs ~20 GB free)
VXZ_KS=packaging/vixzenos-edu.ks sudo -E ./build-vixzenos.sh   # Edu variant

scripts/vixzen-rpm-build.sh              # builds RPMs from a staged SOURCES tree
```

Prefer `--check-only` over a full build. It runs every app's `--smoke` test and
catches almost everything a 40-minute ISO build would.

## 5. Conventions

**Shared code lives in `shared/vixzen_core/`.** One implementation, not five
copies:

- `config.py` — per-app JSON settings under `~/.config/vixzen/`. `load()` merges
  over defaults and **never raises**; corrupt files yield defaults and are backed
  up once beside the original. Pure stdlib — safe to import from tests.
- `style.py` — one `Gtk.CssProvider` helper for every app. Imports `Gtk` **lazily**
  so headless contexts don't crash.
- `__init__.py` — re-exports exactly
  `load, save, path, provider_for, refresh, apply_display, inform`.

Consumers put `shared/` on `sys.path` and import `vixzen_core`. Follow that
pattern; do not add new copies of config or CSS logic into individual apps.

**Every app carries a `--smoke` flag** and must keep it working. Verified output:

```bash
python3 apps/file-manager/vixzen_files.py --smoke          # files smoke OK v0.3
python3 apps/system-settings/vixzen_settings.py --smoke     # settings smoke OK v0.3
python3 apps/power-menu/vixzen_power.py --smoke             # startmenu v4 smoke OK: ...
python3 apps/web-browser/vixzen_web.py --smoke              # web smoke OK v1.1 (WebKit API v6)
python3 preview/src/vixzen_preview.py --smoke               # smoke OK: design tokens + CSS ...
```

(`apps/web-browser-blink/vixzen_blink.py --smoke` runs too, but is skipped when no
Qt WebEngine bindings are present — the build script guards it.)

If you add an app, add a `--smoke` entry AND wire it into `build-vixzenos.sh`
(the block that runs each app's smoke test) or it will not be covered.

**Tests** (`tests/`): headless, plain `assert`, no pytest required to write one.
They insert repo-root `shared/` and `preview/src/` onto `sys.path`, and isolate
`HOME` to a tempdir so they never touch real user config. Preserve both.

**Kickstarts**: `packaging/vixzenos.ks` (Personal) and
`packaging/vixzenos-edu.ks` (Edu). Edu has real polkit rules
(`packaging/edu-polkit/*.rules`) with rule tests — change them, update the tests.

## 6. Hard constraints — do not violate

1. **`build-vixzenos.sh` must never partition a disk or touch a bootloader**
   without an explicit flag. It is documented as "safe by default". Never weaken
   that.
2. **The preview prototype never edits real files** — mock data only. Keep the
   file mock listing `~` read-only.
3. **Any performance claim needs a measurement** against `docs/PERFORMANCE.md`
   budgets. Do not assert "faster" or "lighter" without a number.
4. **No proprietary assets.** Original artwork only; upstream Fedora/GNOME remain
   theirs and the project is unaffiliated — do not ship or imply endorsement.
5. **`scripts/de-fedora.sh` exists to scrub Fedora branding.** Keep changes
   de-brandable.
6. **Design tokens are fixed** (`docs/ARCHITECTURE.md` §3): accent blue
   `#3B82F6` (system `accent-color='blue'`), cyan `#06B6D4`, radius 10px, 8pt spacing grid,
   Cantarell, SVG icons, no heavy blur/3D by default.

## 7. Adding something new

| You're adding… | Put it in |
|---|---|
| A GTK4 app | `apps/<name>/<file>.py`, import config+styling from `vixzen_core` |
| Shell behaviour | `desktop/shell/` (extension) — bar goes in `desktop/panel/` |
| Artwork | `assets/` — SVG preferred; large rasters bloat the ISO |
| A build/theme step | `scripts/vixzen-*.sh` |
| A regression test | `tests/test_<area>.py`, run with `python3 -m pytest tests/ -q` |

## 8. ECC tooling that fits this repo

Reviewers worth delegating to: `python-reviewer` (PEP8, typing, idioms),
`security-reviewer` (polkit rules, `sudo` paths in shell scripts, `dd`/ISO
handling), `silent-failure-hunter` (this repo has `try/except` around config loads
and smoke tests — easy places to swallow real errors), `performance-optimizer`.

Commands: `/verify` and `/quality-gate .` before a commit; `/python-review .`;
`/orch-fix-defect` for a bug proven with a red test; `/skill-create` to distill a
repeated maintenance task.

## 9. Current state

Version **0.3**. Recent work: the **Vixzen Palette** command surface
(`desktop/shell/palette.js` + `fuzzy.js`, keyboard-first, real fuzzy ranking),
ISO host-look parity, Edu polkit fixes, and a maintainer publish runbook
(`docs/PUBLISH.md`) covering COPR + release + ISO upload.

Git branch `main`. ~15.6k tracked files. Keep commits conventional and scoped.
