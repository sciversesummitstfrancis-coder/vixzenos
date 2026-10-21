# VixzenOS Hardware Checklist (M6) — Dell Latitude 3570 first, then others

Boot the ISO on real hardware (try-without-install; Fedora install untouched).
Mark each `[ ]` as you go. Target machine: i5-6200U, 8 GB RAM, Intel HD 520.

## 1. Machine under test

- [ ] Model: ............  CPU: ............  RAM: ............  GPU: ............
- [ ] BIOS mode: UEFI / Legacy ............  Secure Boot: on / off ............
- [ ] ISO used: ............  (file + sha256)
- [ ] Written with: ............ (Media Writer / dd, device: ............)

## 2. Boot

- [ ] GRUB menu shows "Start VixzenOS" first and boots without keys
- [ ] No emergency mode, no dracut errors (Esc during splash shows log)
- [ ] Boot splash shows Vixzen mark (not Fedora), no text errors
- [ ] Time to login/desktop: ............ sec

## 3. Desktop (liveuser, no install)

- [ ] Burst wallpaper visible, dock (dash-to-dock) centered at bottom
- [ ] No top bar (hidetopbar); Activities reachable via Super
- [ ] Vixzen icons (indigo folders), globe Firefox icon
- [ ] Vixzen Files opens `~`; Settings opens; Power menu opens
- [ ] `vix doctor` runs in terminal (Super+T, type `vix doctor`)

## 4. Hardware

- [ ] Wi-Fi connects and survives 5 min
- [ ] Sound plays (Settings → Sound test)
- [ ] Display: native resolution, no tearing while dragging windows
- [ ] Suspend/resume works, session intact after resume
- [ ] USB ports / Bluetooth (as equipped): ............
- [ ] Battery indicator present (laptops)

## 5. Edge cases

- [ ] Second machine (if available): model ............, result ............
- [ ] Secure Boot ON boot: works / fails (note exact error): ............
- [ ] Install-to-disk dry run (spare disk/VM only — never the Fedora disk)

## 6. Sign-off

- [ ] All boxes above green (or failures filed as issues with photos)
- [ ] Notes: ............

File issues with: ISO name, machine, failing box, photo of the error screen.
