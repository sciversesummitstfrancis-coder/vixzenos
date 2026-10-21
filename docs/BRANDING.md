# VixzenOS Branding — where your name shows, and the BIOS question

## What we branded (all inside the ISO — your Fedora host is untouched)
| Place | How | File |
|---|---|---|
| Desktop + apps accent | 3 brand accents (Indigo/Cyan/Ember), pickable in Preview Settings + Vixzen Settings | `preview/src/design.py` (`ACCENTS`) |
| Login screen / About | `PRETTY_NAME="VixzenOS 0.3..."`, hostname `vixzen` | kickstart `%post` → `/etc/os-release`, `/etc/hostname` |
| Terminal greeting | Vixzen ASCII + version | kickstart `%post` → `/etc/motd` |
| Boot menu (GRUB) | Entries say **VixzenOS**, logo wallpaper behind the menu | `/boot/grub2/vixzen-background.png` + `GRUB_DISTRIBUTOR="VixzenOS"` |
| Boot artwork source | 13 KB total, generated offline, committed | `assets/boot/background.png`, `logo.png`, `make_boot_art.py` |

## The BIOS question (honest answer)
**We cannot put our name in the BIOS itself.** The BIOS/UEFI firmware lives on
a chip on the motherboard — changing it means flashing firmware, which is
hardware-specific, risky (a bad flash bricks the machine), and has nothing to
do with an OS project. No Linux distro does this, and we won't try.

**What we CAN own (the parts you actually see):**
1. **UEFI boot entry** — when VixzenOS is installed on a machine, the firmware
   boot menu lists it as **"VixzenOS"**. Created at install time only:
   `efibootmgr --create --label "VixzenOS" --loader '\EFI\vixzen\grubx64.efi'`
   (documented, never run automatically, real hardware only).
2. **GRUB menu** — branded (done above).
3. **Boot splash (Plymouth)** — Vixzen spinner theme. Stretch goal for
   Milestone 5 (needs theme packaging + initramfs hooks).

So: firmware chip = off limits (by design, for safety). Everything from the
moment you pick a boot device = VixzenOS.
