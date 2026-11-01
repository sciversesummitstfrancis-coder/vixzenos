# VixzenOS Mobile — status, plan, and honest boundaries

> **Status: scoped side project. Nothing here blocks or touches the ISO work.**
> Do not read this as "we are building a phone OS now." It is the staircase and
> the first free rung.

## What this document exists for

The idea of VixzenOS on a phone keeps coming up, and the honest answer is not
"yes" or "no" — it is layered. This page fixes the vocabulary so future
conversations can say "we are on rung 1" instead of relitigating the whole
question every time.

## The three layers (and what each costs)

| Layer | Ports over? | Cost |
|---|---|---|
| The identity — tokens, look, apps | Yes, nearly free | GTK4/Libadwaita apps are already touch-adaptive; design tokens apply directly (accent blue `#3B82F6`) |
| The desktop experience — Palette, dock, launcher as a gesture-driven phone UI | Medium | GNOME Shell is being built mobile-first upstream; our surfaces map onto it, but the mapping is design work, not a copy |
| The OS base — kernel, modem, touch, GPU, per-device drivers | Hard | This is per-device engineering measured in months; it is *not* what "porting VixzenOS" means |

**Policy:** Rungs 1–2 are in scope for this repo. Rung 3 (own kernel/device
bring-up) stays out of scope until rung 2 ships something a person can hold.

## Rung 1 — headless ARM prototype in QEMU (the free one)

Goal: prove the app layer + shell pieces run on ARM, using only the laptop we
already target. No new hardware, no money, no risk to the ISO.

### Checklist (each step done = checked, with the date)

- [ ] Install `qemu-system-aarch64` and get a Fedora aarch64 cloud image
      booting headless (SSH in).
- [ ] In the Arm VM: `dnf install python3-gobject gtk4 libadwaita` and run
      `apps/file-manager/vixzen_files.py --smoke` (or an equivalent headless
      smoke — GTK apps can smoke-test with the Broadway/wayland-backend
      trick; record which method worked and the exact output).
- [ ] Same for `vixzen_core` config/style helpers (already pure-stdlib — this
      should pass unmodified).
- [ ] Record the ARM behavior deltas found (missing packages, API versions,
      anything that needed a tweak) in a notes section below.
- [ ] Install Debian arm64 + repeat one app smoke, to confirm the app layer is
      not accidentally Fedora-tied.

**Pass condition:** at least one Vixzen app runs its smoke test on ARM Linux
unmodified, and we can list exactly which pieces were not port-free.

**Fail condition:** apps need a fork (not a tweak) to run on ARM — at that
point rung 2 must wait until the fork is understood and fixed.

## Rung 2 — a real phone, borrowed base

When rung 1 passes, pick **one** postmarketOS-supported phone (candidates the
community rates most usable: Poco X3 NFC, OnePlus 6, Pixel 3a) and flash:

1. postmarketOS + GNOME Shell mobile as the base (borrowed, not forked).
2. Vixzen apps + theme on top, side-loaded.
3. Honestly document what feels wrong on a 6-inch screen; that list is the
   design brief for the mobile shell work.

**Out of scope for rung 2:** modem bring-up, locking our own boot chain,
adaptive shell redesign beyond mapping the Palette.

## Rung 3 — "VixzenOS Mobile" as an independent OS (deliberately deferred)

Only after rung 2: fork the OS-layer parts we dislike, own boot/signing,
maintain a device matrix. This is the war we are choosing *not* to start today.

## Honest boundaries (read before promising anyone a phone)

- No performance claims without a measurement against a documented budget
  (repo rule #3 applies to phones doubly — mobile hw is slower than the
  2015 laptop).
- The Noise hardware that prompted this is **not** flashable: its firmware is
  a signed proprietary RTOS with no unlock path. Any "we'll OS-swap a cheap
  Noisefit-class watch" plan ends at that wall; open-hardware watches
  (PineTime-class) are the only step in that direction that does not dead-end.
- This page is a plan, not a status report. If a checklist item above is
  unchecked, it has not been done — do not let anyone — including us —
  describe MOBILE.md as "in progress" beyond the boxes actually ticked.
